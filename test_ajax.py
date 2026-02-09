import requests

url = "https://www.bernabei.it/vino-online/?isAjax=1&p=2"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    print(f"Content Start: {response.text[:500]}")
    
    try:
        json_data = response.json()
        print("Response is JSON")
        print(f"Keys: {json_data.keys()}")
        product_list_content = json_data.get('productlist', '')
        print(f"Product List Type: {type(product_list_content)}")
        print(f"Product List Start: {product_list_content[:500]}")
    except ValueError:
        print("Response is NOT JSON")

except Exception as e:
    print(f"Error: {e}")
