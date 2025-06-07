import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Создаём папку sessions, если её нет
if not os.path.exists("sessions"):
    os.makedirs("sessions")

# Доступ к TG каналам (API_ID, API_HASH, SESSION_NAME) храним в переменных окружения
API_ID_LIST = [int(os.getenv("API_ID_1")), int(os.getenv("API_ID_2"))]
API_HASH_LIST = [os.getenv("API_HASH_1"), os.getenv("API_HASH_2")]
SESSION_NAMES = [os.getenv("SESSION_NAME_1"), os.getenv("SESSION_NAME_2")]
JSONDB_API_URL = os.getenv("JSONDB_API_URL", "http://localhost:8001/channels") 