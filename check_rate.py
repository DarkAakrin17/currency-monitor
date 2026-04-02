import requests
import json
import os
import datetime

RATE_FILE    = "rate.json"
HISTORY_FILE = "history.json"

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/EURINR=X"
HEADERS   = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ── Yahoo Finance ────────────────────────────────────────────────────────────
def get_rate():
    """Fetch current EUR → INR mid-market rate from Yahoo Finance."""
    params = {"interval": "1m", "range": "1d"}
    resp   = requests.get(YAHOO_URL, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    return float(result["meta"]["regularMarketPrice"])

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(msg):
    token   = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    url     = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)

# ── Persistence ───────────────────────────────────────────────────────────────
def load_last_rate():
    if os.path.exists(RATE_FILE):
        with open(RATE_FILE) as f:
            return json.load(f).get("rate")
    return None

def save_rate(rate, now_ist):
    with open(RATE_FILE, "w") as f:
        json.dump({
            "rate":    rate,
            "updated": now_ist.strftime("%Y-%m-%d %H:%M IST"),
            "source":  "Yahoo Finance"
        }, f)

def update_history(rate, now_ist):
    entry = {"time": now_ist.isoformat(), "rate": rate}

    data = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            data = json.load(f)

    data.append(entry)
    data = data[-300:]   # keep last 300 entries

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

# ── Alert ─────────────────────────────────────────────────────────────────────
def build_alert(last, current, now_str):
    diff = current - last
    pct  = abs(diff) / last * 100
    if abs(diff) < 0.10:
        return None
    arrow  = "📈" if diff > 0 else "📉"
    word   = "Rose" if diff > 0 else "Dropped"
    sign   = "+" if diff > 0 else ""
    return (
        f"{arrow} <b>EUR/INR {word}!</b>\n"
        f"Previous : ₹{last:.4f}\n"
        f"Current  : ₹{current:.4f}\n"
        f"Change   : {sign}₹{diff:.4f}  ({sign}{pct:.2f}%)\n"
        f"Source   : Yahoo Finance\n"
        f"🕐 {now_str}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    now_str = now_ist.strftime("%d %b %Y, %I:%M %p IST")

    current  = get_rate()
    last     = load_last_rate()

    print(f"[{now_str}] EUR → INR: ₹{current:.4f}  (Yahoo Finance)")

    if last and last > 0:
        alert = build_alert(last, current, now_str)
        if alert:
            send_telegram(alert)
            print("Alert sent.")
        else:
            print(f"No significant change (prev ₹{last:.4f}).")
    else:
        print("No previous rate — skipping alert.")

    save_rate(current, now_ist)
    update_history(current, now_ist)

if __name__ == "__main__":
    main()
