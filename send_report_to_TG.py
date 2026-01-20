import json
import os
import requests
import time
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения (Term: Environment Variables)
load_dotenv() 

# Константы (Term: Configuration)
STATUS_FILE = 'last_status.json'
THREE_HOURS = 3 * 60 * 60

# Получаем данные из системы или из .env файла
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
REPORT_URL = os.getenv('REPORT_URL', 'https://github.com')

def get_last_state():
    """Загружает историю предыдущего запуска (Term: Persistence)."""
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "unknown", "timestamp": time.time(), "last_alert_at": 0}

def send_telegram(message, silent=False):
    """Отправляет уведомление со счетчиком и кнопкой без закрепов (Term: Message Editing)."""
    if not TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN or CHAT_ID not found!")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    edit_url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    
    try:
        # 1. Первая стадия: Сообщение и уведомление о 20 секундах
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

        # 2. Вторая стадия: Ожидание 10 секунд и обновление текста
        time.sleep(10)
        requests.post(edit_url, json={
            "chat_id": CHAT_ID,
            "message_id": msg_id,
            "text": message + "\n\n⏳ <i>Generating report... 10s</i>",
            "parse_mode": "HTML"
        })

        # 3. Финальная стадия: Еще 10 секунд и добавление кнопки (Term: Sync Delay)
        time.sleep(10)
        fresh_report_url = f"{REPORT_URL}?t={int(time.time())}" # Cache Busting
        keyboard = {"inline_keyboard": [[{"text": "📊 Open report", "url": fresh_report_url}]]}
        
        edit_payload = {
            "chat_id": CHAT_ID,
            "message_id": msg_id,
            "text": message, 
            "parse_mode": "HTML",
            "reply_markup": json.dumps(keyboard)
        }
        requests.post(edit_url, json=edit_payload)

        print(f"✅ Message sent. Button added after 20s sync.")
    except Exception as e:
        print(f"⚠️ Failed to manage telegram message: {e}")

# def format_duration(seconds):
#     """Превращает секунды в читаемый формат (Term: Formatting)."""
#     mins = int(seconds // 60)
#     return f"{mins} min." if mins > 0 else "less than 1 minute"

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_report_to_TG.py <status>")
        return
    
    current_status = sys.argv[1].lower()
    last_state = get_last_state()
    now = time.time()
    
    #downtime = format_duration(now - last_state.get('timestamp', now))
    last_alert_diff = now - last_state.get('last_alert_at', 0)

    msg = ""
    is_silent = False
    should_send = False

    # Логика уведомлений
    if current_status == "passed" and last_state['status'] == "failed":
        msg = f"✅ <b>RESOLVED</b>: Site is available\n\n🔔 @MishaNovo @ulans2 @ram333n"
        should_send = True
    elif current_status == "failed" and last_state['status'] != "failed":
        msg = f"🚨 <b>ALERT</b>: The site is unavailable!\n\n🔔 @MishaNovo @ulans2 @ram333n"
        should_send = True
    elif current_status == "failed" and last_state['status'] == "failed":
        msg = f"⚠️ <b>Status Update</b>: The site is still not working!"
        is_silent = True
        should_send = True
    elif current_status == "passed" and last_alert_diff > THREE_HOURS:
        msg = f"🟢 <b>Heartbeat</b>: The site is available\nMonitoring is active"
        is_silent = True
        should_send = True

    if should_send:
        send_telegram(msg, silent=is_silent)
        last_state['last_alert_at'] = now

    if current_status != last_state['status']:
        last_state['timestamp'] = now
    
    last_state['status'] = current_status
    with open(STATUS_FILE, 'w') as f:
        json.dump(last_state, f)

if __name__ == "__main__":
    main()