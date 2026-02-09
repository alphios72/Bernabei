import csv
from sqlmodel import Session, select
from database import engine
from models import Product, PriceHistory
from datetime import datetime

def export_to_csv(filename="bernabei_products.csv"):
    with Session(engine) as session:
        statement = select(Product)
        products = session.exec(statement).all()
        
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';') # Use semicolon for Excel compatibility in IT locale
            
            # Header
            writer.writerow([
                "Bernabei Code", "Name", "Current Price", "Ordinary Price", 
                "Lowest Price 30 Days", "Tags", "Category", 
                "Last Checked", "Link", "Image URL"
            ])
            
            for product in products:
                # Get latest history for details
                statement_history = select(PriceHistory)\
                    .where(PriceHistory.product_id == product.id)\
                    .order_by(PriceHistory.timestamp.desc())
                latest_history = session.exec(statement_history).first()
                
                tags = latest_history.tags if latest_history else ""
                ord_price = str(latest_history.ordinary_price).replace('.', ',') if latest_history and latest_history.ordinary_price else ""
                low_price = str(latest_history.lowest_price_30_days).replace('.', ',') if latest_history and latest_history.lowest_price_30_days else ""
                curr_price = str(product.current_price).replace('.', ',') if product.current_price else ""
                
                writer.writerow([
                    product.bernabei_code,
                    product.name,
                    curr_price,
                    ord_price,
                    low_price,
                    tags,
                    product.category,
                    product.last_checked_at,
                    product.product_link,
                    product.image_url
                ])
                
        print(f"Exported {len(products)} products to {filename}")

if __name__ == "__main__":
    export_to_csv("bernabei_export.csv")
