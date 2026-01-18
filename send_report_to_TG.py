import json
import os
import requests
import time
import sys
from dotenv import load_dotenv  # 1. Добавили поддержку .env

# Загружаем переменные окружения (Term: Environment Variables)
load_dotenv() 

# Константы (Term: Configuration)
STATUS_FILE = 'last_status.json'
THREE_HOURS = 36
#THREE_HOURS = 3 * 60 * 60

# Получаем данные из системы или из .env файла
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
# На локалке REPORT_URL возьмется из .env, на GitHub — из YAML
REPORT_URL = os.getenv('REPORT_URL', 'https://github.com')

def get_last_state():
    """Загружает историю предыдущего запуска (Term: Persistence)."""
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "unknown", "timestamp": time.time(), "last_alert_at": 0}

def send_telegram(message, silent=False):
    """Отправляет уведомление через Telegram API (Term: Request)."""
    if not TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN or CHAT_ID not found!")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_notification": silent
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Message sent. Silent: {silent}")
    except Exception as e:
        print(f"Failed to send message: {e}")

def format_duration(seconds):
    """Превращает секунды в читаемый формат (Term: Formatting)."""
    mins = int(seconds // 60)
    return f"{mins} min." if mins > 0 else "less than 1 minute"

def main():
    if len(sys.argv) < 2:
        print("Usage: python send_report_to_TG.py <status>")
        return
    
    current_status = sys.argv[1].lower()
    last_state = get_last_state()
    now = time.time()
    
    # Расчет времени с момента изменения статуса (Term: Time Difference)
    downtime = format_duration(now - last_state.get('timestamp', now))
    last_alert_diff = now - last_state.get('last_alert_at', 0)

    msg = ""
    is_silent = False
    should_send = False

    # 1. Логика RECOVERY (Починилось)
    if current_status == "passed" and last_state['status'] == "failed":
        msg = (
        f"✅ *RESOLVED*: Site is available. Was unavailable: {downtime}\n\n"
        f"🔔 @admin_user1 @admin_user2\n"
        f"[Open report]({REPORT_URL})"
        )
        should_send = True

    # 2. Логика FIRST ALERT (Упало впервые)
    elif current_status == "failed" and last_state['status'] != "failed":
        msg = (
        f"🚨 *ALERT*: The site is unavailable!\n\n"
        f"🔔 @admin_user1 @admin_user2\n"
        f" [Open report]({REPORT_URL})"
        )
        should_send = True

    # 3. Логика STILL FAILING (Повторное падение — Silent Mode)
    elif current_status == "failed" and last_state['status'] == "failed":
        msg = (
        f"⚠️ *Status Update*: The site is still not working! (Total time: {downtime})\n"
        f"[Open report]({REPORT_URL})"
        )
        is_silent = True
        should_send = True

    # 4. Логика HEARTBEAT (Раз в 3 часа)
    elif current_status == "passed" and last_alert_diff > THREE_HOURS:
        msg = f"🟢 *Heartbeat*: The site is available\nMonitoring is active (every 3 hours)"
        is_silent = True
        should_send = True

    if should_send:
        send_telegram(msg, silent=is_silent)
        last_state['last_alert_at'] = now

    # Обновляем "таймер" только если статус изменился (Term: State Management)
    if current_status != last_state['status']:
        last_state['timestamp'] = now
    
    last_state['status'] = current_status
    
    with open(STATUS_FILE, 'w') as f:
        json.dump(last_state, f)

if __name__ == "__main__":
    main()