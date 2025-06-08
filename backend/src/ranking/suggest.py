import requests
import time
import random
from typing import Optional, Dict, Any
from analysis_stock_market import MoexStockAnalyzer


class OrionGPTClient:
    BASE_URL = "https://gpt.orionsoft.ru/api/External"

    def __init__(self, operating_system_code: int, api_key: str, user_domain_name: str):
        self.operating_system_code = operating_system_code
        self.api_key = api_key
        self.user_domain_name = user_domain_name
        self.session = requests.Session()

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}") from e

    def post_new_request(self, dialog_identifier: str, message: str, ai_model_code: int = 1) -> Dict[str, Any]:
        """Отправляет новый запрос в диалог"""
        payload = {
            "operatingSystemCode": self.operating_system_code,
            "apiKey": self.api_key,
            "userDomainName": self.user_domain_name,
            "dialogIdentifier": dialog_identifier,
            "aiModelCode": ai_model_code,
            "Message": message
        }
        return self._make_request("PostNewRequest", payload)

    def get_new_response(self, dialog_identifier: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "operatingSystemCode": self.operating_system_code,
            "apiKey": self.api_key,
        }

        if dialog_identifier:
            payload["dialogIdentifier"] = dialog_identifier

        return self._make_request("GetNewResponse", payload)

    def complete_session(self, dialog_identifier: str) -> Dict[str, Any]:
        payload = {
            "operatingSystemCode": self.operating_system_code,
            "apiKey": self.api_key,
            "dialogIdentifier": dialog_identifier
        }
        return self._make_request("CompleteSession", payload)

    def ask_and_get_answer(
        self,
        dialog_identifier: str,
        message: str,
        wait_seconds: int = 1,
        retries: int = 120,
        raise_on_error: bool = True
    ) -> Optional[Dict[str, Any]]:
        self.post_new_request(dialog_identifier, message)

        for attempt in range(retries):
            time.sleep(wait_seconds)
            try:
                response = self.get_new_response(dialog_identifier)
                if response.get('data'):
                    return response
            except Exception:
                if attempt == retries - 1 and raise_on_error:
                    raise
                continue

        if raise_on_error:
            raise Exception("No response received after several retries")
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

def get_random_chars(input_string, num_chars):
    if num_chars > len(input_string):
        return ''.join(random.shuffle(list(input_string)))
    return ''.join(random.sample(input_string, num_chars))

def make_suggest(client, texts, candles):
    dialog_id = get_random_chars(texts, 30)
    response = client.ask_and_get_answer(
        dialog_id,
        f"""
На основе последних новостей и данных котировок индекса MOEX предоставь развернутый анализ для трейдера. d 

**1. Анализ новостей:**  
- Кратко выдели ключевые события из новостей: {texts}  
- Оцени их потенциальное влияние на рынок (позитивное/негативное/нейтральное).  
- Укажи возможные отрасли или акции, которые могут быть затронуты.  

**2. Технический анализ котировок:**  
- Доступные данные: колонки {candles.columns} (например, Open, High, Low, Close, Volume).  
- Последние значения: {candles.tail(3).values.tolist()} (выведи последние 3 свечи для наглядности).  
- Определи текущий тренд (восходящий/нисходящий/боковик) и ключевые уровни поддержки/сопротивления.  
- Проанализируй объемы: есть ли аномалии или признаки накопления/распределения?  

**3. Торговые рекомендации:**  
- Какие сценарии возможны в ближайшие дни?  
- Какие уровни стоит мониторить для входа/выхода?  
- Какие риски стоит учитывать?  

**4. Альтернативные сценарии:**  
- Что может усилить текущий тренд?  
- Что может развернуть рынок?  

Ответ предоставь в четкой структуре с выделением ключевых выводов.  
"""
    )

    client.complete_session(dialog_id)

    return response['data']['context'][-1]['responseMessage']