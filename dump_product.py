import requests
from bs4 import BeautifulSoup

def fetch_and_analyze(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Fetching {url}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        product_list = soup.find_all('li', class_='item')
        if product_list:
            first_product = product_list[0]
            with open("first_product.html", 'w', encoding='utf-8') as f:
                f.write(first_product.prettify())
            print("Saved first product HTML to first_product.html")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_analyze("https://www.bernabei.it/vino-online/")
