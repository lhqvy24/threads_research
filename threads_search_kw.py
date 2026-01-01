import os, requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
BASE = "https://graph.threads.net/v1.0"

def get(path, **params):
    if not TOKEN:
        raise RuntimeError("Missing THREADS_ACCESS_TOKEN in .env")
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# -------- CONFIG --------
KEYWORD = "Taipei startup"   # đổi từ khóa tại đây (hỗ trợ Unicode)
FIELDS = ",".join([
    "id",
    "text",            # hoặc 'caption' tùy media type
    "permalink",
    "created_time",
    "media_type",
    "author",
    "like_count",
    "reply_count"
])
LIMIT  = 25

# Lọc thời gian (tùy chọn). Bỏ None nếu không cần.
SINCE = "2025-09-01T00:00:00Z"   # hoặc None
UNTIL = "2025-09-20T23:59:59Z"   # hoặc None
# ------------------------

def keyword_search(keyword, fields, limit=25, since=None, until=None, max_pages=None):
    """
    Trả về một list các item tìm được theo keyword.
    - max_pages: giới hạn số trang để tránh loop quá lâu (None = đi hết).
    """
    params = {
        "keyword": keyword,
        "fields": fields,
        "limit": limit
    }
    if since: params["since"] = since
    if until: params["until"] = until

    results = []
    data = get("/keyword_search", **params)

    page_count = 0
    while True:
        page_count += 1
        items = data.get("data", [])
        results.extend(items)

        # dừng nếu không còn trang tiếp
        paging = data.get("paging", {})
        next_url = paging.get("next")

        # nếu muốn giới hạn số trang
        if max_pages is not None and page_count >= max_pages:
            break

        if not next_url:
            break

        # gọi trang kế tiếp (next_url đã có token & cursors)
        r = requests.get(next_url, timeout=30)
        r.raise_for_status()
        data = r.json()

    return results

if __name__ == "__main__":
    items = keyword_search(KEYWORD, FIELDS, limit=LIMIT, since=SINCE, until=UNTIL)
    print(f"Found {len(items)} posts for keyword='{KEYWORD}'")
    for i, it in enumerate(items[:10], 1):  # in thử 10 dòng đầu
        print(f"{i:02d}. {it.get('created_time')}  {it.get('permalink')}")
        # nếu cần text:
        # print("   ", (it.get('text') or "").replace("\n", " ")[:140])