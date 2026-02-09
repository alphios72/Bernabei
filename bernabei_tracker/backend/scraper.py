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
    # Ensure clean base path without query params for pagination appending
    if "?" in url_suffix:
        clean_suffix = url_suffix.split("?")[0]
    else:
        clean_suffix = url_suffix
        
    full_base_url = f"{base_url}{clean_suffix}" if not clean_suffix.startswith("http") else clean_suffix
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    all_products_data = []
    page = 1
    last_page_product_ids = set()
    
    while True:
        # Construct parameters for AJAX
        params = {
            'isAjax': 1,
            'p': page
        }
        
        print(f"Scraping page {page}: {full_base_url} with params {params}...")
        
        try:
            response = requests.get(full_base_url, headers=headers, params=params)
            
            if response.status_code == 404:
                print(f"Page {page} returned 404. Stopping.")
                break
            response.raise_for_status()
            
            try:
                json_data = response.json()
                html_content = json_data.get('productlist', '')
            except ValueError:
                # Fallback if not JSON (maybe first page isn't ajax? or blocking?)
                print(f"Page {page} did not return JSON. Falling back to text.")
                html_content = response.text

            soup = BeautifulSoup(html_content, 'html.parser')
            product_list = soup.find_all('li', class_='item')
            
            if not product_list:
                print(f"No products found on page {page}. Stopping.")
                break
            
            page_products = []
            current_page_ids = set()
            
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

                    current_page_ids.add(p_id)

                    # Image
                    img_elem = product.find('img')
                    image_url = img_elem.get('src') if img_elem else None
                    
                    # Prices
                    current_price = None
                    lowest_price = None
                    ordinary_price = None 
                    
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
                    
                    product_data = {
                        "bernabei_code": p_id,
                        "name": name,
                        "product_link": link,
                        "image_url": image_url,
                        "price": current_price,
                        "ordinary_price": ordinary_price,
                        "lowest_price_30_days": lowest_price,
                        "tags": ",".join(tags) if tags else "",
                        "timestamp": datetime.utcnow()
                    }
                    page_products.append(product_data)
                    
                except Exception as e:
                    print(f"Error parsing product: {e}")
                    continue
            
            if not page_products:
                print(f"No valid products parsed on page {page}. Stopping.")
                break
                
            # Check for duplicates (Finite Scroll Loop Detection)
            # If the set of IDs on this page matches the set of IDs on the last page, we are looping.
            # This handles sites that return page N content for any page > N.
            if page > 1 and current_page_ids == last_page_product_ids:
                 print(f"Page {page} content is identical to page {page-1}. Reached end of infinite scroll. Stopping.")
                 break
            
            last_page_product_ids = current_page_ids
            all_products_data.extend(page_products)
            print(f"Added {len(page_products)} products from page {page}.")
            
            page += 1
            time.sleep(1) # Be polite
            
        except Exception as e:
            print(f"Error fetching URL {current_url}: {e}")
            break
            
    return all_products_data

if __name__ == "__main__":
    # Test
    data = scrape_category_page("/vino-online/")
    print(f"Scraped {len(data)} products.")
    if data:
        print(data[0])
