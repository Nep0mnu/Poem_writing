TOKEN = "7549403834:AAE28RQf9pj0FhQo8CQ_Z2Km56nkqFTz3IQ"
ADMIN_IDS = {1299103295}  # Укажите ID админов
# Ваш API-ключ
API_KEY = "AQVNyI-Wmjes5gyd4_u1LF_zMptXNZKGsDwK27Pt"

# ID папки в Яндекс.Облаке
FOLDER_ID = "b1grk2og9qmmtu1j950f"

URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

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