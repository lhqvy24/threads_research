import re, sys, requests

PATTERNS = [
    r'"user_id"\s*:\s*"(\d+)"',
    r'"profile_id"\s*:\s*"(\d+)"',
    r'data-opaque-userid="(\d+)"',
]

def resolve_username(username: str) -> str | None:
    url = f"https://www.threads.net/@{username}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html = r.text
    for pat in PATTERNS:
        m = re.search(pat, html)
        if m:
            return m.group(1)
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python resolve_threads_id.py <username> [<username> ...]")
        sys.exit(1)
    for u in sys.argv[1:]:
        try:
            uid = resolve_username(u)
            print(f"{u}: {uid or 'NOT FOUND'}")
        except Exception as e:
            print(f"{u}: ERROR {e}")

#mottorieu: 73221451930
#tiemmaysfarm: 72044876248
