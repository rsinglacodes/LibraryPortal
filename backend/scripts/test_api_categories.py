import json
import urllib.request
import urllib.parse

def test_api_categories():
    base = "http://127.0.0.1:8000/api"
    # 1. Get Categories
    with urllib.request.urlopen(f"{base}/books/categories") as resp:
        cats = json.loads(resp.read().decode("utf-8"))
    print("Categories list returned by API:", len(cats))
    for c in cats:
        print("  -", c)

    # 2. Test querying each category
    print("\nQuerying books by category from live API:")
    for cat in cats:
        encoded = urllib.parse.quote(cat)
        url = f"{base}/books?category={encoded}&size=5"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"Category '{cat}': Total {data.get('total')} books found. Sample: {[b['title'] for b in data.get('items', [])[:2]]}")

if __name__ == "__main__":
    test_api_categories()
