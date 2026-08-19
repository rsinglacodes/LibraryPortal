import json
import urllib.request
import urllib.error

def http_post(url, data, headers=None):
    if headers is None:
        headers = {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)

def http_get(url, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)

def test_live_server():
    base = "http://127.0.0.1:8000"
    print("Testing /health...")
    status, res = http_get(f"{base}/health")
    print("Health:", status, res)

    print("\nTesting /api/auth/login with demo user 276804...")
    status, res = http_post(f"{base}/api/auth/login", {"roll_number": "276804", "password": "LibraryUser@276804"})
    print("Login status:", status)
    token = None
    if status == 200:
        token = res.get("access_token")
        print("Login Success! User:", res.get("user"))
    else:
        print("Login error:", res)

    print("\nTesting /api/books?q=Birdsong...")
    status, res = http_get(f"{base}/api/books?q=Birdsong")
    print("Books status:", status, "Items count:", len(res.get("items", [])) if isinstance(res, dict) else res)

    print("\nTesting /api/chat...")
    status, res = http_post(f"{base}/api/chat", {"message": "Recommend some books", "session_id": "test_session"})
    print("Chat status:", status)
    if status == 200:
        print("Chat response snippet:", res.get("response", "")[:100])
        print("Suggested books:", len(res.get("suggested_books", [])))
    else:
        print("Chat error:", res)

    if token:
        print("\nTesting /api/recommendations (Authenticated)...")
        status, res = http_get(f"{base}/api/recommendations?limit=5", headers={"Authorization": f"Bearer {token}"})
        print("Recommendations status:", status)
        if status == 200:
            print(f"Recommendations count: {len(res)}")
            for b in res[:3]:
                print(f" - {b.get('title')} ({b.get('categories')})")
        else:
            print("Recs error:", res)

if __name__ == "__main__":
    test_live_server()
