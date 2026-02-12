from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from database import create_db_and_tables, get_session, verify_db_persistence, engine
from models import Product, PriceHistory, ProductRead
from scraper import scrape_category_page
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from threading import Thread
import time

# Function to run scraping in an infinite loop
def scrape_forever():
    while True:
        try:
            print("Starting scraping cycle...", flush=True)
            run_scrape_job()
            print("Scraping cycle finished. Restarting in 60 seconds...", flush=True)
        except Exception as e:
            print(f"Error in scraping loop: {e}", flush=True)
        
        # Wait a bit before restarting to avoid hammering if job crashes immediately
        time.sleep(60)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    verify_db_persistence()
    
    # Initialize Continuous Scraper in Background Thread
    scraper_thread = Thread(target=scrape_forever, daemon=True)
    scraper_thread.start()
    print("Continuous scraper thread started.", flush=True)


@app.post("/scrape")
def scrape_products(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scrape_job)
    return {"message": "Scraping job started in background"}

def run_scrape_job():
    with Session(engine) as session:
        # Categories to scrape
        categories = ["/vino-online/", "/champagne/"]
        
        for cat in categories:
            try:
                # Scrape logic...
                # Need to import scrape_category_page inside or ensure it's available
                print(f"Starting scrape for {cat}")
                products_data = scrape_category_page(cat)
                
                for p_data in products_data:
                    # Check if product exists
                    # Use unique constraint on bernabei_code
                    statement = select(Product).where(Product.bernabei_code == p_data["bernabei_code"])
                    existing_product = session.exec(statement).first()
                    
                    if not existing_product:
                        existing_product = Product(
                            bernabei_code=p_data.get("bernabei_code"),
                            name=p_data.get("name"),
                            product_link=p_data.get("product_link"),
                            image_url=p_data.get("image_url"),
                            category=cat,
                            current_price=p_data.get("price"),
                            last_checked_at=datetime.utcnow()
                        )
                        session.add(existing_product)
                        session.commit()
                        session.refresh(existing_product)
                    else:
                        existing_product.last_checked_at = datetime.utcnow()
                        if p_data.get("image_url"): existing_product.image_url = p_data.get("image_url")
                        if p_data.get("price"): existing_product.current_price = p_data.get("price")
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
                    
                    should_add_history = False
                    
                    if not last_history:
                        should_add_history = True
                    else:
                        # Check price change
                        if last_history.price != (p_data.get("price") or 0.0):
                             should_add_history = True
                        else:
                            # Check if we have a reading today
                            last_date = last_history.timestamp.date()
                            today_date = datetime.utcnow().date()
                            if last_date != today_date:
                                should_add_history = True
                    
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
                    else:
                        print(f"Skipping history for {existing_product.name} (No change/Already updated today)")
            except Exception as e:
                print(f"Error scraping category {cat}: {e}")
                
        print("Scraping job completed.")

@app.get("/products", response_model=List[ProductRead])
def get_products(session: Session = Depends(get_session)):
    statement = select(Product)
    products = session.exec(statement).all()
    
    result = []
    for p in products:
        # Get history for this product
        hist_statement = select(PriceHistory).where(PriceHistory.product_id == p.id)
        history = session.exec(hist_statement).all()
        
        is_price_ok = False
        is_lowest_all_time = False
        discount_percentage = 0.0
        
        if history and p.current_price:
            prices = [h.price for h in history if h.price > 0]
            if prices:
                # 1. Check if lowest all time
                min_price = min(prices)
                if p.current_price <= min_price:
                    is_lowest_all_time = True
                
                # 2. Check if Price OK (lower than avg last 30 days)
                # Filter last 30 days
                # For simplicity in this iteration we take all history or last N items if 30 days is hard without import timedelta
                # Let's use all history for avg as a proxy or last 30 entries
                avg_price = sum(prices) / len(prices)
                if p.current_price < avg_price:
                    is_price_ok = True
                
                # 3. Discount % against Max
                max_price = max(prices)
                if max_price > 0 and max_price > p.current_price:
                    discount_percentage = ((max_price - p.current_price) / max_price) * 100
        
        # Create Read model
        p_read = ProductRead.from_orm(p)
        p_read.is_price_ok = is_price_ok
        p_read.is_lowest_all_time = is_lowest_all_time
        p_read.discount_percentage = round(discount_percentage, 0)
        
        result.append(p_read)
        
    return result

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
