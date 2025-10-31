import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# --- Основные пути ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets') 

# --- VK ---
VK_TOKEN = os.getenv("VK_TOKEN")
GROUP_ID_RAW = os.getenv("GROUP_ID")

if not VK_TOKEN:
    raise ValueError("❌ VK_TOKEN не задан в .env")
if not GROUP_ID_RAW:
    raise ValueError("❌ GROUP_ID не задан в .env")
    
try:
    GROUP_ID = int(GROUP_ID_RAW)
except ValueError:
     raise ValueError("❌ GROUP_ID должен быть числом")

# --- AI ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QWEN_PROXY_URL = os.getenv("QWEN_PROXY_URL", "http://localhost:3264")

if not OPENROUTER_API_KEY:
    raise ValueError("❌ OPENROUTER_API_KEY не задан в .env")

MODELS = {
    "qwen": "proxy",
    "kimi": "moonshotai/kimi-k2:free",
    "deepseek": "deepseek/deepseek-chat-v3.1:free",
}

# --- Доступ ---
TRUSTED_USER_IDS_RAW = os.getenv("TRUSTED_USER_IDS", "").strip()
TRUSTED_IDS = set()

if TRUSTED_USER_IDS_RAW:
    try:
        TRUSTED_IDS = set(int(x.strip()) for x in TRUSTED_USER_IDS_RAW.split(",") if x.strip())
    except ValueError:
        raise ValueError("❌ Ошибка в TRUSTED_USER_IDS. Должен быть список ID через запятую (напр. 123,456)")
    
# --- Идентификация для OpenRouter ---    
APP_REFERER = os.getenv("APP_REFERER", "https://my-app.com")
APP_TITLE = os.getenv("APP_TITLE", "My VK Bot")

if APP_REFERER == "https://my-app.com":
    print("⚠️ APP_REFERER не задан в .env, OpenRouter может не работать")