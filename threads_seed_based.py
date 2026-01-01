# file: threads_seed_based.py
import os, sys, time, csv, re, datetime, requests
from pathlib import Path
from dotenv import load_dotenv

# ============== CONFIG ==============
SEEDS = ["mottorieu", "tiemmaysfarm"]

# Nếu bạn biết user_id, điền ở đây (ổn định nhất):
MANUAL_ID_MAP = {
    # "mottorieu":   "73221451930",
    # "tiemmaysfarm":"72044876248",
}

MAX_THREADS_PER_USER = 50
MAX_REPLIES_PER_POST = 200
MAX_LIKES_PER_POST   = 500
SLEEP_SEC            = 0.3
FIELDS_POST   = "id,text,caption,permalink,created_time,media_type,like_count,reply_count,author"
FIELDS_REPLY  = "id,text,permalink,created_time,author,like_count,reply_count"
FIELDS_LIKE   = "id,username"
FIELDS_USER   = "id,username,verified"
# ====================================

load_dotenv()
TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
BASE  = "https://graph.threads.net/v1.0"
assert TOKEN, "❌ Missing THREADS_ACCESS_TOKEN in .env"

ts_dir = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
OUTDIR = Path("out") / ts_dir
OUTDIR.mkdir(parents=True, exist_ok=True)

def _log(*a): print(*a, flush=True)
def _sleep(): time.sleep(SLEEP_SEC)

def req(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE}{path}", params=params, timeout=30)
    if r.status_code >= 400:
        try: _log("HTTP ERR", r.status_code, r.json())
        except: _log("HTTP ERR", r.status_code, r.text[:300])
        r.raise_for_status()
    return r.json()

def paged(path, **params):
    data = req(path, **params)
    while True:
        for it in data.get("data", []):
            yield it
        nxt = data.get("paging", {}).get("next")
        if not nxt: break
        data = requests.get(nxt, timeout=30).json()

# --- resolve username fallback ---
def resolve_username_html(username):
    url = f"https://www.threads.net/@{username}"
    r = requests.get(url, timeout=30)
    if r.status_code != 200: return None
    html = r.text
    for pat in [r'"user_id"\s*:\s*"(\d+)"', r'"profile_id"\s*:\s*"(\d+)"', r'data-opaque-userid="(\d+)"']:
        m = re.search(pat, html)
        if m: return m.group(1)
    return None

# --- API helpers ---
def get_user_profile(user_id):
    try: return req(f"/{user_id}", fields=FIELDS_USER)
    except: return {"id": user_id}

def get_user_threads(user_id, limit=MAX_THREADS_PER_USER):
    path = f"/{user_id}/threads"
    items = []
    for it in paged(path, fields=FIELDS_POST, limit=25):
        items.append(it)
        if len(items) >= limit: break
        _sleep()
    return items

def get_replies(media_id, limit=MAX_REPLIES_PER_POST):
    items = []
    try:
        for it in paged(f"/{media_id}/replies", fields=FIELDS_REPLY, limit=50):
            items.append(it)
            if len(items) >= limit: break
    except: pass
    return items

def get_likes(media_id, limit=MAX_LIKES_PER_POST):
    items = []
    try:
        for it in paged(f"/{media_id}/likes", fields=FIELDS_LIKE, limit=100):
            items.append(it)
            if len(items) >= limit: break
    except: pass
    return items

# --- quyền check ---
def can_read_user_threads(user_id: str) -> bool:
    try:
        _ = req(f"/{user_id}/threads", fields="id", limit=1)
        return True
    except requests.HTTPError as e:
        try:
            err = e.response.json().get("error", {})
            if err.get("code") == 100 and err.get("error_subcode") == 33:
                return False
        except: pass
        raise

# --- MAIN ---
def main():
    if len(sys.argv) > 1:
        seeds = sys.argv[1:]
    else:
        seeds = SEEDS

    users_f   = (OUTDIR/"users.csv").open("w",newline="",encoding="utf-8")
    posts_f   = (OUTDIR/"posts.csv").open("w",newline="",encoding="utf-8")
    replies_f = (OUTDIR/"replies.csv").open("w",newline="",encoding="utf-8")
    likes_f   = (OUTDIR/"likes.csv").open("w",newline="",encoding="utf-8")

    uw = csv.DictWriter(users_f,["user_id","username","verified"]); uw.writeheader()
    pw = csv.DictWriter(posts_f,["post_id","author_id","created_time","permalink","media_type","like_count","reply_count","text"]); pw.writeheader()
    rw = csv.DictWriter(replies_f,["post_id","reply_id","author_id","created_time","permalink","like_count","reply_count","text"]); rw.writeheader()
    lw = csv.DictWriter(likes_f,["post_id","user_id","username"]); lw.writeheader()

    seen_users=set()

    for s in seeds:
        uid = MANUAL_ID_MAP.get(s)
        if not uid and not s.isdigit():
            _log(f"🔎 Resolve HTML: {s}")
            uid = resolve_username_html(s)
        if not uid: 
            _log(f"❗ Không resolve được {s}, bỏ qua"); continue

        # profile
        prof=get_user_profile(uid)
        uw.writerow({"user_id":prof.get("id"),"username":prof.get("username") or s,"verified":prof.get("verified")})
        users_f.flush(); seen_users.add(prof.get("id"))
        _log(f"👤 User {prof.get('username') or s} ({uid})")

        # threads (hoặc fallback)
        target=uid
        if not can_read_user_threads(uid):
            _log(f"⚠️ Không có quyền đọc threads {s} ({uid}) → fallback /me")
            target="me"
        threads=get_user_threads(target)
        _log(f"🧵 Threads: {len(threads)}")

        for t in threads:
            post_id=t.get("id"); author=(t.get("author") or {}); aid=author.get("id")
            text=(t.get("text") or t.get("caption") or "").replace("\n"," ")
            pw.writerow({"post_id":post_id,"author_id":aid,"created_time":t.get("created_time"),
                         "permalink":t.get("permalink"),"media_type":t.get("media_type"),
                         "like_count":t.get("like_count"),"reply_count":t.get("reply_count"),"text":text})
            posts_f.flush()

            # replies
            for r in get_replies(post_id):
                ra=(r.get("author") or {}); ra_id=ra.get("id")
                rw.writerow({"post_id":post_id,"reply_id":r.get("id"),"author_id":ra_id,
                             "created_time":r.get("created_time"),"permalink":r.get("permalink"),
                             "like_count":r.get("like_count"),"reply_count":r.get("reply_count"),
                             "text":(r.get("text") or "").replace("\n"," ")})
            replies_f.flush()

            # likes
            for lk in get_likes(post_id):
                lw.writerow({"post_id":post_id,"user_id":lk.get("id"),"username":lk.get("username")})
            likes_f.flush()
            _sleep()

    for f in (users_f,posts_f,replies_f,likes_f): f.close()
    _log(f"✅ Done. Data in {OUTDIR}")

if __name__=="__main__":
    main()