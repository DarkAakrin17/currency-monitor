import requests
import json
import os
import datetime

RATE_FILE = "rate.json"
HISTORY_FILE = "history.json"

def get_rate():
    url = "https://api.exchangerate-api.com/v4/latest/EUR"
    data = requests.get(url).json()
    return data["rates"]["INR"]

def send_telegram(msg):
    token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

def load_last_rate():
    if os.path.exists(RATE_FILE):
        with open(RATE_FILE, "r") as f:
            return json.load(f)["rate"]
    return None

def save_rate(rate):
    with open(RATE_FILE, "w") as f:
        json.dump({"rate": rate}, f)

def update_history(rate):
    entry = {
        "time": datetime.datetime.utcnow().isoformat(),
        "rate": rate
    }

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(entry)

    # keep last 300 entries
    data = data[-300:]

    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f)

def main():
    current_rate = get_rate()
    last_rate = load_last_rate()

    print(f"Current rate: {current_rate}")

    if last_rate is not None:
        drop = last_rate - current_rate

        if drop > 0.1:
            send_telegram(
                f"📉 EUR dropped!\nOld: {last_rate}\nNew: {current_rate}\nDrop: {round(drop, 3)}"
            )

    save_rate(current_rate)
    update_history(current_rate)

if __name__ == "__main__":
    main()
