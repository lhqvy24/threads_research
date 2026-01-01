import os, requests
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("THREADS_ACCESS_TOKEN")
BASE = "https://graph.threads.net/v1.0"

def get(path, **params):
    params["access_token"] = TOKEN
    r = requests.get(f"{BASE}{path}", params=params)
    r.raise_for_status()
    return r.json()

# me
print(get("/me"))

# threads
me = get("/me")
uid = me["id"]
threads = get(f"/{uid}/threads",
              fields="id,caption,permalink,created_time,like_count,reply_count")
print(threads)