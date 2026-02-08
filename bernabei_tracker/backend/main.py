from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from sqlmodel import Session, select
from typing import List, Optional
from database import create_db_and_tables, get_session, engine
from models import Product, PriceHistory
from scraper import scrape_category_page
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bernabei Price Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.post("/scrape")
def scrape_products(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_scrape_job)
    return {"message": "Scraping job started in background"}

def run_scrape_job():
    with Session(engine) as session:
        # Categories to scrape
        categories = ["/vino-online/", "/spiriti-online/"] #, "/bollicine-online/"
        
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
                            last_checked_at=datetime.utcnow()
                        )
                        session.add(existing_product)
                        session.commit()
                        session.refresh(existing_product)
                    else:
                        existing_product.last_checked_at = datetime.utcnow()
                        if p_data.get("image_url"): existing_product.image_url = p_data.get("image_url")
                        session.add(existing_product)
                        session.commit()
                        session.refresh(existing_product)
                    
                    # Add Price History
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
                print(f"Error scraping category {cat}: {e}")
                
        print("Scraping job completed.")

@app.get("/products", response_model=List[Product])
def get_products(session: Session = Depends(get_session)):
    statement = select(Product)
    products = session.exec(statement).all()
    return products

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
