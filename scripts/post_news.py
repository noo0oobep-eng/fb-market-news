# scripts/post_news.py
# Posts fresh market headlines to a Facebook Page.
# Needs env vars: FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN

import os, sys, time, re
import requests, feedparser
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparse
import random
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
def add_utm(url, source="facebook", medium="social", campaign="market_news", content="auto"):
    p = urlparse(url); q = dict(parse_qsl(p.query))
    q.update({"utm_source": source, "utm_medium": medium, "utm_campaign": campaign, "utm_content": content})
    return urlunparse(p._replace(query=urlencode(q)))

CTA_LINKS = [
    "👉 Buy Oil Navigator Pro: https://buy.stripe.com/7sY4gBfCw1Wb9yz0jhdjO00",
    "👉 More tools & docs: https://www.aptradingtools.com/?utm_source=fb&utm_medium=post"
]
def pick_cta():
    return random.choice(CTA_LINKS)

PAGE_ID = os.getenv("FB_PAGE_ID")
TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")

if not PAGE_ID or not TOKEN:
    print("Missing FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN env vars.", file=sys.stderr)
    sys.exit(1)

FEEDS = [
    # Markets / Business
    "https://www.reuters.com/finance/markets/rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Top news & analysis
    # Forex
    "https://www.dailyfx.com/feeds/market-news",              # Forex news
    # Crypto
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
]

HASHTAGS = "#markets #stocks #forex #crypto #trading"

# consider items in the last 24h
NOW = datetime.now(timezone.utc)
CUTOFF = NOW - timedelta(hours=24)

def is_recent(entry):
    # Try published/updated dates; fall back to now if missing
    for key in ("published", "updated", "pubDate"):
        val = getattr(entry, key, None) or (entry.get(key) if isinstance(entry, dict) else None)
        if val:
            try:
                dt = dtparse.parse(val)
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt >= CUTOFF
            except Exception:
                pass
    return True  # if no date, assume recent

def pick_items(max_items=3):
    picked = []
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                if is_recent(entry):
                    title = getattr(entry, "title", "").strip()
                    link = getattr(entry, "link", "").strip()
                    if title and link and not any(link == x["link"] for x in picked):
                        picked.append({"title": title, "link": link})
                        break  # take only the first fresh item from this feed
        except Exception as e:
            print(f"[WARN] Failed to read feed {url}: {e}")
        if len(picked) >= max_items:
            break
    return picked

# Use first URL in message to improve preview/unfurl
URL_RE = re.compile(r'https?://\S+')

def post_to_facebook(message: str):
    endpoint = f"https://graph.facebook.com/v20.0/{PAGE_ID}/feed"
    try:
        message = f"{message}\n\n{pick_cta()}"
    except NameError:
        pass
    m = re.search(r'https?://\S+', message)
    data = {"message": message, "access_token": TOKEN}
    if m:
        raw = m.group(0).rstrip(').,;')
        url = add_utm(raw)                 # add tracking
        data["link"] = url                 # preview card uses UTM link
        message = message.replace(raw, url, 1)
        data["message"] = message
    resp = requests.post(endpoint, data=data, timeout=30)
    if resp.ok:
        print("[OK] Posted:", resp.json()); return True
    print("[ERR]", resp.status_code, resp.text); return False

def main():
    items = pick_items(max_items=3)  # change to 1 if you want only one post per run
    if not items:
        print("No fresh items found.")
        return

    for idx, it in enumerate(items, start=1):
        msg = f"{it['title']}\n{it['link']}\n\n{HASHTAGS}"
        print(f"Posting {idx}/{len(items)}: {it['title']}")
        post_to_facebook(msg)
        # Small pause to avoid rate-bursting
        time.sleep(3)

if __name__ == "__main__":
    main()
