# file: threads_search_min.py
import os, sys, requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
BASE  = "https://graph.threads.net/v1.0"

def get(path, **params):
    if not TOKEN:
        raise SystemExit("❌ Missing THREADS_ACCESS_TOKEN in .env")
    params["access_token"] = TOKEN
    try:
        r = requests.get(f"{BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        # In ra nội dung lỗi server để debug (500, 4xx…)
        print(f"HTTPError: {e}")
        if r is not None:
            print("Response text:", r.text[:500])
        raise

def keyword_search_min(keyword, limit=10, max_pages=1):
    """Minimal keyword search: fields = id,text,permalink"""
    params = {
        "q": keyword,
        "fields": "id,text,permalink",
        "limit": limit,
        # Thêm since/until nếu muốn:
        # "since": "2025-09-01T00:00:00Z",
        # "until": "2025-09-20T23:59:59Z",
    }
    data = get("/keyword_search", **params)
    results = []
    page = 0
    while True:
        page += 1
        results.extend(data.get("data", []))
        if page >= max_pages:
            break
        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break
        data = requests.get(next_url, timeout=30).json()
    return results

if __name__ == "__main__":
    keyword = " ".join(sys.argv[1:]) or "test"
    print(f"🔎 Searching keyword: {keyword!r}")
    items = keyword_search_min(keyword, limit=10, max_pages=1)
    print(f"✅ Found {len(items)} items")
    for i, it in enumerate(items[:10], 1):
        print(f"{i:02d}. {it.get('permalink')}")
        # Nếu cần xem text:
        # print("   ", (it.get('text') or "").replace("\n"," ")[:120])