from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from database import create_db_and_tables, get_session, verify_db_persistence, engine
from models import Product, PriceHistory, ProductRead
from scraper import scrape_category_page, BlockingError
from analytics import calculate_convenience_score
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from threading import Thread
import time

app = FastAPI(title="Bernabei Price Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to run scraping in an infinite loop
def scrape_forever():
    current_cat_idx = 0
    current_page = 1
    
    while True:
        try:
            print(f"Starting scraping cycle from Category Index {current_cat_idx}, Page {current_page}...", flush=True)
            run_scrape_job(start_category_idx=current_cat_idx, start_page=current_page)
            print("Scraping cycle finished. Restarting in 60 seconds...", flush=True)
            
            # Reset state on successful completion
            current_cat_idx = 0
            current_page = 1
            
        except BlockingError as e:
            print(f"Scraper blocked at Category Index {getattr(e, 'category_index', 0)}, Page {e.page_number}!", flush=True)
            print("Sleeping for 30 minutes before resuming...", flush=True)
            
            # Save state to resume later
            current_cat_idx = getattr(e, 'category_index', 0)
            current_page = e.page_number
            
            time.sleep(1800)
            continue
        except Exception as e:
            print(f"Error in scraping loop: {e}", flush=True)
        
        # Wait a bit before restarting to avoid hammering if job crashes immediately
        time.sleep(60)

def ensure_convenience_score_column():
    """Manually add column if missing because SQLModel create_all doesn't alter existing tables"""
    from sqlalchemy import text
    with Session(engine) as session:
        try:
            # Try selecting the column to see if it exists
            session.exec(text("SELECT convenience_score FROM product LIMIT 1"))
        except Exception:
            print("Adding missing 'convenience_score' column to product table...", flush=True)
            try:
                session.exec(text("ALTER TABLE product ADD COLUMN convenience_score FLOAT"))
                session.commit()
            except Exception as e:
                print(f"Error adding column: {e}", flush=True)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    verify_db_persistence()
    ensure_convenience_score_column()
    
    # Initialize Continuous Scraper in Background Thread
    scraper_thread = Thread(target=scrape_forever, daemon=True)
    scraper_thread.start()
    print("Continuous scraper thread started.", flush=True)


@app.post("/scrape")
def scrape_products(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scrape_job)
    return {"message": "Scraping job started in background"}

# Helper function to save a batch of products to DB
# This is called by the scraper after each page
def save_products_to_db(products_data: List[dict]):
    if not products_data: return
    
    with Session(engine) as session:
        for p_data in products_data:
            try:
                # Improved Deduplication Logic
                # 1. Try finding by Bernabei Code (ID)
                statement = select(Product).where(Product.bernabei_code == p_data["bernabei_code"])
                existing_product = session.exec(statement).first()
                
                # 2. If not found by ID, try finding by CLEAN URL SLUG
                # This prevents "soft duplicates" where ID extraction fails or changes slightly
                if not existing_product:
                    products = session.exec(select(Product)).all()
                    
                    # Extract current slug
                    current_link = p_data.get("product_link", "")
                    current_slug = None
                    if current_link:
                         current_slug = current_link.split('?')[0].strip('/').split('/')[-1]

                    if current_slug:
                        # Scan existing products for same slug
                        # This is slightly slower but safer against duplicates
                        # Given dataset size (<10k), it's acceptable for now or we can index slug
                        for p in products:
                            if p.product_link:
                                p_slug = p.product_link.split('?')[0].strip('/').split('/')[-1]
                                if p_slug == current_slug:
                                    existing_product = p
                                    break
                
                # 3. If still not found, try by Exact Name match (fallback for no-link items)
                if not existing_product and p_data.get("name"):
                    statement = select(Product).where(Product.name == p_data.get("name"))
                    existing_product = session.exec(statement).first()
                
                if not existing_product:
                    existing_product = Product(
                        bernabei_code=p_data.get("bernabei_code"),
                        name=p_data.get("name"),
                        product_link=p_data.get("product_link"),
                        image_url=p_data.get("image_url"),
                        # Category might be missing in p_data so defaulting to empty string
                        category=p_data.get("category", ""), 
                        current_price=p_data.get("price") or 0.0,
                        last_checked_at=datetime.utcnow()
                    )
                    session.add(existing_product)
                    session.commit()
                    session.refresh(existing_product)
                else:
                    # Update existing product
                    existing_product.last_checked_at = datetime.utcnow()
                    
                    # If we found it by slug/name but the incoming data has a better ID (not a hash), update ID?
                    # Let's keep existing ID stable unless it lacks one.
                    # Or maybe update image/price
                    if p_data.get("image_url"): existing_product.image_url = p_data.get("image_url")
                    
                    current_p = p_data.get("price")
                    if current_p is not None:
                         existing_product.current_price = current_p
                         
                    # Also update link if changed (e.g. redirect)
                    if p_data.get("product_link"):
                        existing_product.product_link = p_data.get("product_link")

                    session.add(existing_product)
                    session.commit()
                    session.refresh(existing_product)
                
                # Add Price History
                # Add Price History Logic
                # Rules:
                # 1. New Product -> Add
                # 2. No reading today -> Add
                # 3. Price changed -> Add
                
                # Get last history entry
                last_history = session.exec(
                    select(PriceHistory)
                    .where(PriceHistory.product_id == existing_product.id)
                    .order_by(PriceHistory.timestamp.desc())
                ).first()
                
                # User request: "vorrei conservare nel database tutte le rilevazioni"
                # We save every reading regardless of price change or date.
                should_add_history = True
                
                # if not last_history:
                #     should_add_history = True
                # else:
                #     # Check price change
                #     if last_history.price != (p_data.get("price") or 0.0):
                #             should_add_history = True
                #     else:
                #         # Check if we have a reading today
                #         last_date = last_history.timestamp.date()
                #         today_date = datetime.utcnow().date()
                #         if last_date != today_date:
                #             should_add_history = True
                
                if should_add_history:
                    history = PriceHistory(
                        product_id=existing_product.id,
                        price=p_data.get("price") or 0.0,
                        ordinary_price=p_data.get("ordinary_price"),
                        lowest_price_30_days=p_data.get("lowest_price_30_days"),
                        tags=p_data.get("tags"),
                        timestamp=datetime.utcnow()
                    )
                    session.add(history)
                    session.commit()
            except Exception as e:
                print(f"Error saving product {p_data.get('name')}: {e}", flush=True)

def update_all_scores():
    """Background task to update convenience scores for all products"""
    print("Starting batch update of Convenience Scores...", flush=True)
    try:
        with Session(engine) as session:
            products = session.exec(select(Product)).all()
            count = 0
            for p in products:
                # Fetch history
                history = session.exec(select(PriceHistory).where(PriceHistory.product_id == p.id)).all()
                if not history:
                    continue
                
                # Convert to format expected by analytics
                history_data = [{"timestamp": h.timestamp, "price": h.price} for h in history]
                
                # Calculate Score
                current_price = p.current_price or 0.0
                if current_price > 0:
                    score = calculate_convenience_score(history_data, current_price)
                    
                    # Update if changed
                    if p.convenience_score != score:
                        p.convenience_score = score
                        session.add(p)
                        count += 1
            
            session.commit()
            print(f"Convenience Scores updated for {count} products.", flush=True)
    except Exception as e:
        print(f"Error updating scores: {e}", flush=True)

def run_scrape_job(start_category_idx=0, start_page=1):
    # Categories to scrape
    categories = ["/vino-online/", "/champagne/"]
    
    for i, cat in enumerate(categories):
        # Skip categories we've already done
        if i < start_category_idx:
            continue
            
        try:
            # Determine start page for this category
            # If we are resuming the same category where we stopped, use start_page.
            # Otherwise (new category), start from 1.
            current_start_page = start_page if i == start_category_idx else 1
            
            # Scrape logic...
            print(f"Starting scrape for {cat} from page {current_start_page}", flush=True)
            
            # Define a closure or partial to pass category info if needed
            # We'll create a wrapper function to inject the category
            def save_callback_wrapper(batch):
                # Inject category into each item
                for item in batch:
                    item['category'] = cat
                save_products_to_db(batch)
            
            # Pass the callback and start_page to the scraper
            scrape_category_page(cat, save_callback=save_callback_wrapper, start_page=current_start_page)
            
        except BlockingError as e:
            print(f"BlockingError in category {cat} at page {e.page_number}. Stopping job to trigger cooldown.", flush=True)
            # Attach the current category index to the exception so the main loop knows where to resume
            e.category_index = i
            raise e
        except Exception as e:
            print(f"Error scraping category {cat}: {e}", flush=True)
            
    print("Scraping job completed.", flush=True)
    
    # Trigger Score Update after full scrape
    try:
        update_all_scores()
    except Exception as e:
        print(f"Failed to run score update after scrape: {e}", flush=True)

@app.get("/products", response_model=List[ProductRead])
def get_products(session: Session = Depends(get_session)):
    # Optimized query to avoid N+1 problem
    # We fetch products and aggregated history stats in one go.
    from sqlalchemy import text
    
    query = text("""
    SELECT 
        p.id, p.bernabei_code, p.name, p.product_link, p.image_url, 
        p.category, p.current_price, p.last_checked_at, p.convenience_score,
        MIN(h.price) as min_price,
        AVG(h.price) as avg_price,
        MAX(h.price) as max_price
    FROM product p
    LEFT JOIN pricehistory h ON p.id = h.product_id AND h.price > 0
    GROUP BY p.id
    """)
    
    results = session.exec(query).all()
    
    products_read = []
    for row in results:
        # Unpack row
        # Order matches SELECT
        p_id, code, name, link, img, cat, curr, last_check, score, min_p, avg_p, max_p = row
        
        # Determine stats
        is_lowest = False
        is_price_ok = False
        discount = 0.0
        
        if curr and min_p is not None:
            if curr <= min_p:
                is_lowest = True
            
            if avg_p and curr < avg_p:
                is_price_ok = True
                
            if max_p and max_p > curr:
                discount = ((max_p - curr) / max_p) * 100
        
        # Build Read Model
        p_read = ProductRead(
            id=p_id,
            bernabei_code=code,
            name=name,
            product_link=link,
            image_url=img,
            category=cat,
            current_price=curr,
            last_checked_at=last_check,
            convenience_score=round(score, 1) if score is not None else None,
            is_price_ok=is_price_ok,
            is_lowest_all_time=is_lowest,
            discount_percentage=round(discount, 0)
        )
        products_read.append(p_read)
        
    return products_read

@app.get("/products/{product_id}/history", response_model=List[PriceHistory])
def get_product_history(product_id: int, session: Session = Depends(get_session)):
    statement = select(PriceHistory).where(PriceHistory.product_id == product_id).order_by(PriceHistory.timestamp)
    history = session.exec(statement).all()
    return history

@app.get("/products/{product_id}", response_model=Product)
def get_product_details(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Serve static files if they exist (for single-container deployment)
# This MUST be after all API routes to avoid shadowing them
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
