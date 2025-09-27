# scripts/post_news.py
import os, time, requests, feedparser
from datetime import datetime, timezone

FB_USER_TOKEN = os.environ["FB_USER_TOKEN"]
FB_PAGE_ID    = os.environ["FB_PAGE_ID"]
API_VER       = "v23.0"

FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/marketsNews",
    "https://www.coindesk.com/arc/outboundfeeds/rss/"
]

def get_page_token(user_token, page_id):
    url = f"https://graph.facebook.com/{API_VER}/me/accounts"
    r = requests.get(url, params={"access_token": user_token}, timeout=30)
    r.raise_for_status()
    for pg in r.json().get("data", []):
        if pg.get("id") == page_id:
            return pg.get("access_token")
    raise SystemExit("Could not find Page access token. Is this user an admin of the Page?")

def collect_headlines(max_items=3):
    seen = set()
    items = []
    for feed in FEEDS:
        d = feedparser.parse(feed)
        for e in d.entries[:6]:
            title = e.get("title", "").strip()
            link  = e.get("link", "").strip()
            if not title or not link or link in seen: 
                continue
            seen.add(link)
            # Use published time if available
            ts = None
            if "published_parsed" in e and e.published_parsed:
                ts = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
            items.append({"title": title, "link": link, "ts": ts})
    # newest first when we have timestamps
    items.sort(key=lambda x: x["ts"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[:max_items]

def post_to_page(page_token, page_id, title, link):
    url = f"https://graph.facebook.com/{API_VER}/{page_id}/feed"
    message = f"{title}\n\n{link}\n\n#markets #forex #stocks #crypto"
    r = requests.post(url, data={"message": message, "access_token": page_token}, timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Post failed: {r.status_code} {r.text}")
    print("Posted:", r.json())

def main():
    page_token = get_page_token(FB_USER_TOKEN, FB_PAGE_ID)
    headlines = collect_headlines(max_items=2)  # post 2 items per run
    if not headlines:
        print("No headlines found.")
        return
    for h in headlines:
        post_to_page(page_token, FB_PAGE_ID, h["title"], h["link"])
        time.sleep(5)  # tiny pause between posts

if __name__ == "__main__":
    main()
