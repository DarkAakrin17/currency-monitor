import requests
import json
import os
import datetime
import re

RATE_FILE    = "rate.json"
HISTORY_FILE = "history.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Google Finance ────────────────────────────────────────────────────────────
def get_rate():
    """Fetch EUR → INR mid-market rate from Google Finance."""
    resp = requests.get(
        "https://www.google.com/finance/quote/EUR-INR",
        headers=HEADERS, timeout=10
    )
    resp.raise_for_status()

    # Primary: data-last-price attribute
    m = re.search(r'data-last-price="([0-9.]+)"', resp.text)
    if m:
        return float(m.group(1))

    # Fallback: YMlKec fxKbKc span
    m = re.search(r'class="YMlKec fxKbKc"[^>]*>([0-9,]+\.[0-9]+)<', resp.text)
    if m:
        return float(m.group(1).replace(",", ""))

    raise ValueError("Could not parse EUR-INR rate from Google Finance page")

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(msg):
    token   = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
        timeout=10
    )

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
            "source":  "Google Finance"
        }, f)

def update_history(rate, now_ist):
    data = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            data = json.load(f)
    data.append({"time": now_ist.isoformat(), "rate": rate})
    data = data[-300:]
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

# ── Alert ─────────────────────────────────────────────────────────────────────
def build_alert(last, current, now_str):
    diff = current - last
    pct  = abs(diff) / last * 100
    if abs(diff) < 0.10:
        return None
    arrow = "📈" if diff > 0 else "📉"
    word  = "Rose" if diff > 0 else "Dropped"
    sign  = "+" if diff > 0 else ""
    return (
        f"{arrow} <b>EUR/INR {word}!</b>\n"
        f"Previous : ₹{last:.4f}\n"
        f"Current  : ₹{current:.4f}\n"
        f"Change   : {sign}₹{diff:.4f}  ({sign}{pct:.2f}%)\n"
        f"Source   : Google Finance\n"
        f"🕐 {now_str}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    now_str = now_ist.strftime("%d %b %Y, %I:%M %p IST")

    current = get_rate()
    last    = load_last_rate()

    print(f"[{now_str}] EUR → INR: ₹{current:.4f}  (Google Finance)")

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
