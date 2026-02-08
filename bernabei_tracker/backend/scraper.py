import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import time

def parse_price(price_str):
    if not price_str: return None
    # Remove euro sign and non-breaking spaces, replace comma with dot
    clean_str = re.sub(r'[^\d,\.]', '', price_str).replace(',', '.')
    # Remove trailing dots if any (e.g. from thousand separators if used differently)
    # Euro standard for Italy is 1.000,00 but usually simple sites use 1000,00
    try:
        return float(clean_str)
    except ValueError:
        return None

def extract_product_id(product_elem):
    # Try finding the add-to-cart button which contains product ID in onclick or class
    try:
        btn = product_elem.find('button', class_='btn-cart')
        if btn:
            # onclick=".../product/19132/..."
            onclick = btn.get('onclick', '')
            match = re.search(r'/product/(\d+)/', onclick)
            if match:
                return match.group(1)
            
        # Fallback: check price id "product-price-19132..."
        prices = product_elem.find_all(id=re.compile(r'product-price-'))
        for p in prices:
            match = re.search(r'product-price-(\d+)', p['id'])
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def scrape_category_page(url_suffix):
    base_url = "https://www.bernabei.it"
    full_url = f"{base_url}{url_suffix}" if not url_suffix.startswith("http") else url_suffix
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Scraping {full_url}...")
    try:
        response = requests.get(full_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        product_list = soup.find_all('li', class_='item')
        
        products_data = []
        
        for product in product_list:
            try:
                # Name & Link
                title_elem = product.find('h3', class_='item-title')
                if not title_elem: continue
                
                link_elem = title_elem.find('a')
                if not link_elem: continue
                
                name = link_elem.get_text(strip=True)
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = f"{base_url}{link}"
                
                # ID
                p_id = extract_product_id(product)
                if not p_id: 
                    # fallback to generating one from link slug
                    p_id = link.split('/')[-1] if link else f"unknown_{int(time.time()*1000)}"

                # Image
                img_elem = product.find('img')
                image_url = img_elem.get('src') if img_elem else None
                
                # Prices
                current_price = None
                lowest_price = None
                ordinary_price = None # Often labeled as old-price if on sale
                
                price_box = product.find('div', class_='price-box')
                if price_box:
                    # Current Price
                    special_price_elem = price_box.find('p', class_='special-price')
                    if special_price_elem:
                        current_price = parse_price(special_price_elem.find('span', class_='price').get_text(strip=True))
                    else:
                        regular_price_elem = price_box.find('span', class_='regular-price')
                        if regular_price_elem:
                            current_price = parse_price(regular_price_elem.find('span', class_='price').get_text(strip=True))
                    
                    # Lowest Price (Comparative)
                    prev_price_elem = price_box.find('p', class_='previous-price')
                    if prev_price_elem:
                        # Sometimes labeled "Prezzo più basso:"
                        lowest_price = parse_price(prev_price_elem.find('span', class_='price').get_text(strip=True))
                    
                    # Old/Ordinary Price
                    old_price_elem = price_box.find('p', class_='old-price')
                    if old_price_elem:
                        ordinary_price = parse_price(old_price_elem.find('span', class_='price').get_text(strip=True))

                # Tags
                tags = []
                promo_labels = product.find_all(class_=re.compile(r'promo-label|ico-product|label'))
                for label in promo_labels:
                    txt = label.get_text(strip=True)
                    if txt: tags.append(txt)
                
                products_data.append({
                    "bernabei_code": p_id,
                    "name": name,
                    "product_link": link,
                    "image_url": image_url,
                    "price": current_price,
                    "ordinary_price": ordinary_price,
                    "lowest_price_30_days": lowest_price,
                    "tags": ",".join(tags) if tags else "",
                    "timestamp": datetime.utcnow()
                })
                
            except Exception as e:
                print(f"Error parsing product: {e}")
                continue
                
        return products_data
        
    except Exception as e:
        print(f"Error fetching URL {full_url}: {e}")
        return []

if __name__ == "__main__":
    # Test
    data = scrape_category_page("/vino-online/")
    print(f"Scraped {len(data)} products.")
    if data:
        print(data[0])
