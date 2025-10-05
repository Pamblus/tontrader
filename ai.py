from openai import OpenAI
import re
from config import AI_API_KEY, AI_BASE_URL, AI_MODEL

class AITrader:
    def __init__(self):
        self.client = OpenAI(
            api_key=AI_API_KEY,
            base_url=AI_BASE_URL,
        )
        self.model = AI_MODEL
    
    def call_ai(self, messages):
        """Вызов API ИИ через aitunnel"""
        try:
            response = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                max_tokens=50000,
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Ошибка AI: {str(e)}"
    
    def parse_ai_response(self, response):
        """Парсинг ответа ИИ на команды"""
        commands = {
            'action': None,
            'instrument': None,
            'direction': None,
            'amount': None,
            'leverage': None,
            'close_trade': None,
            'comment': None
        }
        
        # Парсим действия
        action_match = re.search(r'<действие=([^>]+)>', response)
        if action_match:
            commands['action'] = action_match.group(1)
        
        # Парсим инструмент
        instrument_match = re.search(r'<instrument=([^>]+)>', response)
        if instrument_match:
            commands['instrument'] = instrument_match.group(1)
        
        # Парсим направление
        direction_match = re.search(r'<direction=([^>]+)>', response)
        if direction_match:
            commands['direction'] = direction_match.group(1)
        
        # Парсим сумму
        amount_match = re.search(r'<amount=([^>]+)>', response)
        if amount_match:
            commands['amount'] = amount_match.group(1)
        
        # Парсим плечо
        leverage_match = re.search(r'<leverage=([^>]+)>', response)
        if leverage_match:
            commands['leverage'] = leverage_match.group(1)
        
        # Парсим закрытие сделки
        close_match = re.search(r'<close_trade=([^>]+)>', response)
        if close_match:
            commands['close_trade'] = close_match.group(1)
        
        # Парсим комментарий
        comment_match = re.search(r'<comment>([^<]+)</comment>', response)
        if comment_match:
            commands['comment'] = comment_match.group(1).strip()
        
        return commands
