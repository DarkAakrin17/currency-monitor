import requests
import json
import os
import datetime
import re

RATE_FILE = "rate.json"
HISTORY_FILE = "history.json"

# ── Google Finance scraper ──────────────────────────────────────────────────
def get_rate():
    """Fetch EUR → INR rate from Google Finance (no API key needed)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    url = "https://www.google.com/finance/quote/EUR-INR"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    # Google Finance embeds the price in a data-last-price attribute
    match = re.search(r'data-last-price="([0-9.]+)"', resp.text)
    if match:
        return float(match.group(1))

    # Fallback: look for the YMlKec fxKbKc class span (current price text)
    match = re.search(r'class="YMlKec fxKbKc"[^>]*>([0-9,]+\.[0-9]+)<', resp.text)
    if match:
        return float(match.group(1).replace(",", ""))

    raise ValueError("Could not parse EUR-INR rate from Google Finance")

# ── Telegram ────────────────────────────────────────────────────────────────
def send_telegram(msg):
    token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"}, timeout=10)

# ── Persistence ─────────────────────────────────────────────────────────────
def load_last_rate():
    if os.path.exists(RATE_FILE):
        with open(RATE_FILE, "r") as f:
            data = json.load(f)
            return data.get("rate")
    return None

def save_rate(rate):
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    with open(RATE_FILE, "w") as f:
        json.dump({"rate": rate, "updated": now_ist.strftime("%Y-%m-%d %H:%M IST")}, f)

def update_history(rate):
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    entry = {
        "time": now_ist.isoformat(),
        "rate": rate
    }

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(entry)
    data = data[-300:]        # keep last 300 entries

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

# ── Alert logic ─────────────────────────────────────────────────────────────
def build_alert(last_rate, current_rate, now_str):
    drop = last_rate - current_rate
    rise = current_rate - last_rate
    pct  = abs(current_rate - last_rate) / last_rate * 100

    if drop > 0.10:
        return (
            f"📉 <b>EUR/INR Dropped!</b>\n"
            f"Previous : ₹{last_rate:.4f}\n"
            f"Current  : ₹{current_rate:.4f}\n"
            f"Drop     : ₹{drop:.4f}  ({pct:.2f}%)\n"
            f"🕐 {now_str}"
        )
    if rise > 0.10:
        return (
            f"📈 <b>EUR/INR Rose!</b>\n"
            f"Previous : ₹{last_rate:.4f}\n"
            f"Current  : ₹{current_rate:.4f}\n"
            f"Rise     : ₹{rise:.4f}  ({pct:.2f}%)\n"
            f"🕐 {now_str}"
        )
    return None

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    current_rate = get_rate()
    last_rate    = load_last_rate()
    now_ist      = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    now_str      = now_ist.strftime("%d %b %Y, %I:%M %p IST")

    print(f"[{now_str}] EUR → INR: ₹{current_rate:.4f}")

    if last_rate and last_rate > 0:
        alert = build_alert(last_rate, current_rate, now_str)
        if alert:
            send_telegram(alert)
            print("Alert sent.")
        else:
            print(f"No significant change (prev ₹{last_rate:.4f}).")
    else:
        print("No previous rate on record — skipping alert.")

    save_rate(current_rate)
    update_history(current_rate)

if __name__ == "__main__":
    main()
