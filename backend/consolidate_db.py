import logging
from sqlmodel import Session, select, create_engine
from models import Product, PriceHistory
from database import sqlite_file_name as DB_NAME
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Verify DB Path
if not os.path.exists(DB_NAME):
    # Try looking in default locations if running locally/different context
    if os.path.exists(f"../{DB_NAME}"):
        DB_NAME = f"../{DB_NAME}"
    elif os.path.exists(f"backend/{DB_NAME}"):
        DB_NAME = f"backend/{DB_NAME}"

sqlite_url = f"sqlite:///{DB_NAME}"
# Increase timeout to 60 seconds to avoid "database is locked" errors
# if the scraper is running concurrently.
connect_args = {"check_same_thread": False, "timeout": 60}
engine = create_engine(sqlite_url, connect_args=connect_args)

def consolidate_duplicates():
    logger.info("Starting database consolidation...")
    
    with Session(engine) as session:
        # Get all products
        products = session.exec(select(Product)).all()
        logger.info(f"Found {len(products)} total products.")
        
        # Group by a "Key" that represents identity regardless of unstable ID
        # Key = (Normalized Name, Normalized Link Slug)
        grouped = {}
        
        for p in products:
            # key based on link slug for stability
            if p.product_link:
                slug = p.product_link.split('?')[0].strip('/').split('/')[-1]
                key = slug
            else:
                # fallback to name
                key = p.name.strip().lower()
            
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(p)
            
        duplicates_found = 0
        deleted_count = 0
        
        for key, group in grouped.items():
            if len(group) > 1:
                duplicates_found += 1
                logger.info(f"Found duplicate group for key '{key}': {len(group)} entries.")
                
                # Pick the "Master"
                # Preference:
                # 1. The one matching the key if key is extracted ID?
                # 2. The one with most history?
                # 3. The most recently checked?
                
                # Let's sort by valid-looking ID first (no "unknown_" hash) then by history count
                def sort_key(prod):
                    is_hash = "unknown_" in prod.bernabei_code or "gen_" in prod.bernabei_code
                    return (not is_hash, prod.last_checked_at or datetime.min)
                
                group.sort(key=sort_key, reverse=True)
                master = group[0]
                others = group[1:]
                
                # Refresh master to ensure clean state
                session.refresh(master)
                
                for other in others:
                    logger.info(f"  Merging & Deleting: {other.id} ({other.bernabei_code})")
                    
                    # Move history to master
                    history_entries = session.exec(select(PriceHistory).where(PriceHistory.product_id == other.id)).all()
                    
                    if history_entries:
                        for h in history_entries:
                            h.product_id = master.id
                            session.add(h)
                        # Flush the history moves so they are no longer associated with 'other' in the DB
                        session.flush()
                        
                        # Refresh 'other' so it knows its children are gone
                        session.refresh(other)

                    # Delete duplicate product
                    session.delete(other)
                    deleted_count += 1
                    
                    # Commit per group to keep transaction size manageable and save progress
                    session.commit()
        
        session.commit()
        logger.info(f"Consolidation complete. Found {duplicates_found} duplicate groups. Deleted {deleted_count} duplicate products.")

if __name__ == "__main__":
    from datetime import datetime
    try:
        consolidate_duplicates()
    except Exception as e:
        logger.error(f"Error during consolidation: {e}")
