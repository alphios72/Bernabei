import requests
from bs4 import BeautifulSoup
import re

def fetch_and_analyze(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        product_list = soup.find_all('li', class_='item') # Adjust selector if needed
        print(f"Found {len(product_list)} products.")
        
        for i, product in enumerate(product_list[:5]): # Check first 5 items
            print(f"\n--- Product {i+1} ---")
            
            # Name
            name_tag = product.find('h2', class_='product-name')
            name = name_tag.get_text(strip=True) if name_tag else "N/A"
            print(f"Name: {name}")
            
            # Link
            link_tag = product.find('a', class_='product-image')
            link = link_tag['href'] if link_tag else "N/A"
            print(f"Link: {link}")

            # Price
            price_box = product.find('div', class_='price-box')
            if price_box:
                # Regular price or special price
                special_price = price_box.find('p', class_='special-price')
                old_price = price_box.find('p', class_='old-price')
                regular_price = price_box.find('span', class_='regular-price')
                
                if special_price:
                    current_price = special_price.find('span', class_='price').get_text(strip=True)
                    print(f"Current Price (Special): {current_price}")
                elif regular_price:
                    current_price = regular_price.find('span', class_='price').get_text(strip=True)
                    print(f"Current Price (Regular): {current_price}")
                else:
                    print("Current Price: Not found")
                    
                if old_price:
                    op = old_price.find('span', class_='price').get_text(strip=True)
                    print(f"Old Price: {op}")
            else:
                print("Price Box not found")
                
            # Tags
            # Look for labels or badges
            tags = []
            labels = product.find_all(class_=re.compile(r'label|badge|ico-|tag'))
            for label in labels:
                tag_text = label.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            
            # Check for "Popular" text if it was outside standard tags
            # Based on previous output "POPULAR11,90" it might be just text or a span
            # The previous output had "POPULAR" mixed with price.
            
            print(f"Tags found: {tags}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_analyze("https://www.bernabei.it/vino-online/")
