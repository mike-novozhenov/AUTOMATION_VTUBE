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
    """Отправляет уведомление с кнопкой и управляет закрепами (Term: Inline Keyboard)."""
    if not TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN or CHAT_ID not found!")
        return

    # Настройка кнопки под сообщением
    keyboard = {
        "inline_keyboard": [[
            {"text": "📊 Open report", "url": REPORT_URL}
        ]]
    }

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_notification": silent,
        "reply_markup": json.dumps(keyboard) # Добавляем кнопку в запрос
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Telegram API Error: {response.text}")
            return

        result = response.json()
        msg_id = result.get('result', {}).get('message_id')
        
        # Если это не "тихое" сообщение, делаем закреп (Term: Pin)
        if not silent and msg_id:
            # 1. Удаляем все старые закрепы
            requests.post(f"https://api.telegram.org/bot{TOKEN}/unpinAllChatMessages", 
                          json={"chat_id": CHAT_ID})
            
            # 2. Закрепляем новое для всплывашки
            pin_payload = {
                "chat_id": CHAT_ID,
                "message_id": msg_id,
                "disable_notification": False 
            }
            requests.post(f"https://api.telegram.org/bot{TOKEN}/pinChatMessage", json=pin_payload)

        print(f"✅ Message sent with button. Silent: {silent}")
    except Exception as e:
        print(f"⚠️ Failed to send message: {e}")

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
    
    downtime = format_duration(now - last_state.get('timestamp', now))
    last_alert_diff = now - last_state.get('last_alert_at', 0)

    msg = ""
    is_silent = False
    should_send = False

    # 1. Логика RECOVERY
    if current_status == "passed" and last_state['status'] == "failed":
        msg = (
            f"✅ <b>RESOLVED</b>: Site is available. Was unavailable: {downtime}\n\n"
            f"🔔 @MishaNovo @MarynaNovo"
        )
        should_send = True

    # 2. Логика FIRST ALERT
    elif current_status == "failed" and last_state['status'] != "failed":
        msg = (
            f"🚨 <b>ALERT</b>: The site is unavailable!\n\n"
            f"🔔 @MishaNovo @MarynaNovo"
        )
        should_send = True

    # 3. Логика STILL FAILING
    elif current_status == "failed" and last_state['status'] == "failed":
        msg = f"⚠️ <b>Status Update</b>: The site is still not working! (Total time: {downtime})"
        is_silent = True
        should_send = True

    # 4. Логика HEARTBEAT
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