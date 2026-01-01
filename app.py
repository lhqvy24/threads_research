import os, urllib.parse
from flask import Flask, redirect, request
import requests
from dotenv import load_dotenv

load_dotenv()
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = os.getenv("SCOPES", "threads_basic")

AUTH_URL = "https://threads.net/oauth/authorize"
TOKEN_URL = "https://graph.threads.net/oauth/access_token"
EXCHANGE_URL = "https://graph.threads.net/access_token"

app = Flask(__name__)

@app.route("/")
def index():
    # bước 1: đưa user sang Authorization Window để lấy "code"
    params = {
        "client_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "response_type": "code",
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return f'<a href="{url}">Login with Threads</a>'

@app.route("/oauth/callback")
def callback():
    # bước 2: nhận ?code=... từ redirect & đổi sang short-lived access_token
    code = request.args.get("code")
    if not code:
        return "Missing code", 400

    data = {
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }
    r = requests.post(TOKEN_URL, data=data, timeout=30)
    if not r.ok:
        return f"""
        <h3>Token exchange failed</h3>
        <pre>Status: {r.status_code}</pre>
        <pre>Body: {r.text}</pre>
        <pre>client_id(last4): {str(APP_ID)[-4:]}</pre>
        <pre>redirect_uri: {REDIRECT_URI}</pre>
        """, 400
    r.raise_for_status()
    short_token = r.json()["access_token"]
    user_id = r.json().get("user_id")


    # bước 3 (khuyên dùng): đổi sang long-lived token để dùng bền hơn
    ex = requests.get(EXCHANGE_URL, params={
        "grant_type": "th_exchange_token",
        "client_secret": APP_SECRET,
        "access_token": short_token
    }, timeout=30)
    if ex.ok:
        long_token = ex.json()["access_token"]
        token_view = f"<b>Long-lived token</b>: {long_token}"
    else:
        token_view = f"<b>Short-lived token</b>: {short_token}"

    return f"""
    <h3>Threads OAuth OK</h3>
    <p>User ID: {user_id}</p>
    <p>{token_view}</p>
    <p>Test /me: <a href="/me?access_token={short_token}">GET /me</a></p>
    """

@app.route("/me")
def me():
    token = request.args.get("access_token")
    resp = requests.get("https://graph.threads.net/me",
                        params={"access_token": token}, timeout=30)
    return resp.text, resp.status_code, {"Content-Type": "application/json"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000,
            ssl_context=("localhost.pem", "localhost-key.pem"),
            debug=True)