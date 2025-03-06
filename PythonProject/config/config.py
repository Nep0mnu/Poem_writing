TOKEN = ""
ADMIN_IDS = {}  # Укажите ID админов
# Ваш API-ключ
API_KEY = ""

# ID папки в Яндекс.Облаке
FOLDER_ID = ""

URL = ""

# Тело запроса
data = {
    "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.7,
        "maxTokens": 200
    },
    "messages": [
        {"role": "user", "text": "напиши мне 5 новых интересных и сложных метафоричных словосочетаний и коротких предложений"}
    ]
}

# Заголовки
headers = {
    "Authorization": f"Api-Key {API_KEY}",
    "Content-Type": "application/json"
}
