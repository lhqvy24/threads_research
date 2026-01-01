import os, time, csv, requests
from typing import Dict, Iterator, List, Optional
from dotenv import load_dotenv
import os

load_dotenv()  # đọc file .env ở cùng thư mục

APP_ID  = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES")

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
THREADS_USER_ID = os.getenv("THREADS_USER_ID")

BASE = "https://graph.threads.net/v1.0"

def _get(url: str, params: Optional[Dict]=None) -> Dict:
    params = params or {}
    params["access_token"] = THREADS_ACCESS_TOKEN
    r = requests.get(url, params=params, timeout=30)
    if not r.ok:
        raise RuntimeError(f"GET {url} failed {r.status_code}: {r.text}")
    return r.json()

def _paginate(url: str, params: Optional[Dict]=None) -> Iterator[Dict]:
    params = params or {}
    params["access_token"] = THREADS_ACCESS_TOKEN
    while True:
        r = requests.get(url, params=params, timeout=30)
        if not r.ok:
            raise RuntimeError(f"GET {url} failed {r.status_code}: {r.text}")
        payload = r.json()
        for item in payload.get("data", []):
            yield item
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        # next_url đã có đầy đủ query; để lần gọi sau không gửi params nữa
        url, params = next_url, {}
        # nhẹ nhàng tôn trọng rate limit
        time.sleep(0.2)

def fetch_all_posts(fields: str) -> List[Dict]:
    url = f"{BASE}/{THREADS_USER_ID}/threads"
    return list(_paginate(url, {"fields": fields}))

def fetch_replies_for_post(media_id: str, fields: str) -> List[Dict]:
    url = f"{BASE}/{media_id}/replies"
    return list(_paginate(url, {"fields": fields}))

def save_csv(path: str, rows: List[Dict], headers: List[str]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in rows:
            # chỉ ghi các cột có trong headers để tránh key thừa
            w.writerow({k: row.get(k) for k in headers})

def main():
    if not THREADS_ACCESS_TOKEN or "PASTE_" in THREADS_ACCESS_TOKEN:
        raise SystemExit("⚠️  Chưa đặt LONG_TOKEN. Sửa biến LONG_TOKEN ở đầu file hoặc export THREADS_ACCESS_TOKEN trong shell.")
    if not THREADS_USER_ID or "PASTE_" in THREADS_USER_ID:
        raise SystemExit("⚠️  Chưa đặt USER_ID. Sửa biến USER_ID ở đầu file hoặc export THREADS_USER_ID trong shell.")

    # 1) Lấy toàn bộ posts của bạn
    post_fields = "id,caption,permalink,created_time,like_count,reply_count"
    posts = fetch_all_posts(post_fields)
    print(f"✅ Fetched {len(posts)} posts")

    # Lưu posts.csv
    save_csv(
        "threads_posts.csv",
        posts,
        headers=["id", "caption", "permalink", "created_time", "like_count", "reply_count"],
    )
    print("💾 Saved posts -> threads_posts.csv")

    # 2) Lấy replies cho từng post
    reply_fields = "id,text,author,created_time,permalink"
    all_replies = []
    for p in posts:
        mid = p["id"]
        replies = fetch_replies_for_post(mid, reply_fields)
        for r in replies:
            r["media_id"] = mid  # gắn post gốc để join sau này
        all_replies.extend(replies)
        print(f"   • {mid}: {len(replies)} replies")
        time.sleep(0.2)  # nhẹt rate

    # Lưu replies.csv
    save_csv(
        "threads_replies.csv",
        all_replies,
        headers=["id", "media_id", "text", "author", "created_time", "permalink"],
    )
    print(f"💾 Saved replies ({len(all_replies)}) -> threads_replies.csv")

if __name__ == "__main__":
    main()