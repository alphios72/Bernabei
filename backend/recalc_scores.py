from sqlmodel import Session, select, create_engine
from models import Product, PriceHistory
from database import sqlite_file_name
from analytics import calculate_convenience_score
import logging
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verify DB Path
if not os.path.exists(sqlite_file_name):
     # Try standard docker path
    if os.path.exists(f"/app/data/bernabei.db"):
        sqlite_file_name = "/app/data/bernabei.db"
    elif os.path.exists("bernabei.db"):
        sqlite_file_name = "bernabei.db"

sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def update_scores():
    logger.info(f"Starting score recalculation using DB: {sqlite_file_name}...")
    
    with Session(engine) as session:
        # Check column existence hack
        try:
             session.exec(select(Product.convenience_score).limit(1))
        except Exception:
            logger.info("Adding missing 'convenience_score' column...")
            from sqlalchemy import text
            try:
                session.exec(text("ALTER TABLE product ADD COLUMN convenience_score FLOAT"))
                session.commit()
            except Exception as e:
                logger.error(f"Failed to add column: {e}")

        products = session.exec(select(Product)).all()
        total = len(products)
        logger.info(f"Found {total} products. Processing...")
        
        count = 0
        updated = 0
        
        for p in products:
            try:
                history = session.exec(select(PriceHistory).where(PriceHistory.product_id == p.id)).all()
                if not history:
                    continue
                
                history_data = [{"timestamp": h.timestamp, "price": h.price} for h in history]
                current_price = p.current_price or 0.0
                
                if current_price > 0:
                    score = calculate_convenience_score(history_data, current_price)
                    
                    if p.convenience_score != score:
                        p.convenience_score = score
                        session.add(p)
                        updated += 1
                
                count += 1
                if count % 100 == 0:
                    print(f"Processed {count}/{total}...", flush=True)
            except Exception as e:
                logger.error(f"Error processing {p.name}: {e}")
                
        session.commit()
        logger.info(f"Completed! Updated scores for {updated} products.")

if __name__ == "__main__":
    update_scores()
