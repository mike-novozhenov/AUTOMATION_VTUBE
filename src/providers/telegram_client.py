import json
import os
import requests
import time
import sys
from dotenv import load_dotenv

load_dotenv() 

# Configuration and Persistence setup
STATUS_FILE = os.path.join(os.getcwd(), 'last_status.json')
THREE_HOURS = 3 * 60 * 60

TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REPORT_URL = os.getenv('REPORT_URL', 'https://github.com')

def get_last_state():
    """Load the previous execution state (Term: Persistence)."""
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "unknown", "timestamp": time.time(), "last_alert_at": 0}

def send_telegram(message, silent=False):
    """Send notification with a countdown and an inline button (Term: Message Editing)."""
    if not TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN or CHAT_ID not found!")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    edit_url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    
    try:
        # Stage 1: Initial message with 20s sync warning
        payload = {
            "chat_id": CHAT_ID,
            "text": message + "\n\n⏳ <i>Generating report... 20s</i>",
            "parse_mode": "HTML",
            "disable_notification": silent
        }
        
        response = requests.post(url, json=payload)
        res_data = response.json()
        msg_id = res_data.get('result', {}).get('message_id')
        if not msg_id: return

        # Stage 2: Sync delay (update text to 10s)
        time.sleep(10)
        requests.post(edit_url, json={
            "chat_id": CHAT_ID,
            "message_id": msg_id,
            "text": message + "\n\n⏳ <i>Generating report... 10s</i>",
            "parse_mode": "HTML"
        })

        # Stage 3: Final update with Report Button (Term: Cache Busting)
        time.sleep(10)
        fresh_report_url = f"{REPORT_URL}?t={int(time.time())}" 
        keyboard = {"inline_keyboard": [[{"text": "📊 Open report", "url": fresh_report_url}]]}
        
        edit_payload = {
            "chat_id": CHAT_ID,
            "message_id": msg_id,
            "text": message, 
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        requests.post(edit_url, json=edit_payload)

        print(f"✅ Notification delivered. UI synced.")
    except Exception as e:
        print(f"⚠️ Telegram provider error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python telegram_client.py <status>")
        return
    
    current_status = sys.argv[1].lower()
    last_state = get_last_state()
    now = time.time()
    
    last_alert_diff = now - last_state.get('last_alert_at', 0)

    msg = ""
    is_silent = False
    should_send = False

    # Notification Logic (State Machine)
    if current_status == "passed" and last_state['status'] == "failed":
        msg = f"✅ <b>RESOLVED</b>: Site is available\n\n🔔 @MishaNovo @ulans2 @ram333n"
        should_send = True
    elif current_status == "failed" and last_state['status'] != "failed":
        msg = f"🚨 <b>ALERT</b>: The site is unavailable!\n\n🔔 @MishaNovo @ulans2 @ram333n"
        should_send = True
    elif current_status == "failed" and last_state['status'] == "failed":
        msg = f"⚠️ <b>Status Update</b>: The site is still down."
        is_silent = True
        should_send = True
    elif current_status == "passed" and last_alert_diff > THREE_HOURS:
        msg = f"🟢 <b>Heartbeat</b>: System is healthy\nMonitoring active."
        is_silent = True
        should_send = True

    if should_send:
        send_telegram(msg, silent=is_silent)
        last_state['last_alert_at'] = now

    # Update state only on change
    if current_status != last_state['status']:
        last_state['timestamp'] = now
    
    last_state['status'] = current_status
    with open(STATUS_FILE, 'w') as f:
        json.dump(last_state, f)

if __name__ == "__main__":
    main()