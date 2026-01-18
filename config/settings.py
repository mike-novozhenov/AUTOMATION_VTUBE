# Base URL
BASE_URL = "https://erozyx.com"

# Глобальный порог скорости для всех страниц (SLA)
MAX_WAIT_TIME = 0.1

# Список страниц для мониторинга (Endpoints)
# Ты можешь добавлять сюда любые пути
ENDPOINTS = [
    BASE_URL + "/",               # Home
    BASE_URL + "/videos",         # Videos
    BASE_URL + "/categories",     # Niches or Categories list
    BASE_URL + "/channels",       # Channels
    BASE_URL + "/community",       # Community
]
