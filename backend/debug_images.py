from sqlmodel import Session, select, create_engine
from models import Product
from database import sqlite_file_name
import requests
from bs4 import BeautifulSoup
import os

# 1. Check Database
print("--- DATABASE CHECK ---")
if not os.path.exists(sqlite_file_name):
    print(f"DB not found at {sqlite_file_name}")
else:
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    engine = create_engine(sqlite_url)
    with Session(engine) as session:
        products = session.exec(select(Product)).all()
        total = len(products)
        with_img = len([p for p in products if p.image_url])
        print(f"Total Products: {total}")
        print(f"With Image URL: {with_img}")
        
        if with_img > 0:
            print("Sample Image URLs:")
            for p in products[:5]:
                if p.image_url:
                    print(f" - {p.image_url}")

# 2. Check Scraper Logic
print("\n--- SCRAPER CHECK ---")
url = "https://www.bernabei.it/vino-online/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}
try:
    print(f"Fetching {url}...")
    # Proxies?
    proxies = None
    proxy_url = os.getenv("SCRAPER_PROXY")
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}
        print(f"Using proxy: {proxy_url}")

    res = requests.get(url, headers=headers, proxies=proxies, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    
    items = soup.find_all('li', class_='item')
    print(f"Found {len(items)} items.")
    
    if items:
        first = items[0]
        img = first.find('img')
        if img:
            print("First item <img> tag:")
            print(img)
            print(f"src: {img.get('src')}")
            print(f"data-src: {img.get('data-src')}")
            print(f"data-original: {img.get('data-original')}")
        else:
            print("No <img> found in first item")

except Exception as e:
    print(f"Scraper check failed: {e}")
