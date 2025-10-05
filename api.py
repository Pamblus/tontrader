import requests
import json
import time
from config import TRADING_API_KEY, REQUEST_TIMEOUT, TRADING_BASE_URL

class TradingAPI:
    def __init__(self):
        self.base_url = TRADING_BASE_URL  # Используем правильный URL
        self.headers = {
            "Authorization": f"Bearer {TRADING_API_KEY}",
            "accept": "application/json, text/plain, */*",
            "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "content-type": "application/json",
            "sec-ch-ua": "\"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
        }
    
    def get_session(self):
        """Получить данные сессии и баланс"""
        try:
            response = requests.get(
                f"{self.base_url}/users/session",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка получения сессии: {e}")
            return None
    
    def get_instruments(self):
        """Получить список инструментов"""
        try:
            response = requests.get(
                f"{self.base_url}/instruments",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('instruments', [])[:10]
            return []
        except Exception as e:
            print(f"Ошибка получения инструментов: {e}")
            return []
    
    def get_price_history(self, symbol, count=30):
        """Получить историю цен"""
        try:
            response = requests.get(
                f"{self.base_url}/instruments/history/{symbol}/m1?count={count}",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка получения истории {symbol}: {e}")
            return None
    
    def get_closed_trades(self, wallet, from_time, to_time):
        """Получить закрытые сделки с реальным PnL"""
        try:
            response = requests.get(
                f"{self.base_url}/trades/closed/{wallet}?from={from_time}&to={to_time}",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка получения закрытых сделок: {e}")
            return None
    
    def get_active_trades(self):
        """Получить активные сделки"""
        try:
            # Попробуем разные эндпоинты для активных сделок
            response = requests.get(
                f"{self.base_url}/trades/active",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            
            # Если не работает, попробуем другой эндпоинт
            response = requests.get(
                f"{self.base_url}/trades",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else {"trades": []}
            
        except Exception as e:
            print(f"Ошибка получения активных сделок: {e}")
            return {"trades": []}
    
    def get_trade_status(self, trade_id):
        """Получить статус конкретной сделки"""
        try:
            response = requests.get(
                f"{self.base_url}/trades/{trade_id}",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка получения статуса сделки {trade_id}: {e}")
            return None
    
    def get_all_trades_with_profit(self, wallet="DOLLR"):
        """Получить все сделки с реальным PnL"""
        try:
            # Получаем закрытые сделки за последний период
            from_time = 0
            to_time = int(time.time() * 1000)  # Текущее время в мс
            
            closed_trades = self.get_closed_trades(wallet, from_time, to_time)
            active_trades = self.get_active_trades()
            
            # Объединяем все сделки
            all_trades = []
            
            # Добавляем активные сделки
            if active_trades and 'trades' in active_trades:
                for trade in active_trades['trades']:
                    trade['status'] = 'active'
                    trade['current_profit'] = self.calculate_current_profit(trade)
                    all_trades.append(trade)
            
            # Добавляем закрытые сделки
            if closed_trades and 'trades' in closed_trades:
                for trade in closed_trades['trades']:
                    trade['status'] = 'closed'
                    trade['current_profit'] = trade.get('profit', 0)
                    all_trades.append(trade)
            
            return all_trades
            
        except Exception as e:
            print(f"Ошибка получения всех сделок: {e}")
            return []
    
    def calculate_current_profit(self, trade):
        """Рассчитать текущий PnL для активной сделки"""
        try:
            # Получаем текущую цену инструмента
            instruments = self.get_instruments()
            current_instrument = next((inst for inst in instruments if inst['symbol'] == trade['instrument']), None)
            
            if not current_instrument:
                return 0
            
            current_price = float(current_instrument.get('rate', 0))
            open_price = float(trade['open_rate'])
            amount = float(trade['amount'])
            leverage = int(trade['leverage'])
            
            if trade['direction'] == 'buy':
                profit = (current_price - open_price) / open_price * amount * leverage
            else:
                profit = (open_price - current_price) / open_price * amount * leverage
            
            # Учитываем комиссии
            commission = float(trade.get('commission', 0))
            return profit + commission
            
        except Exception as e:
            print(f"Ошибка расчета PnL: {e}")
            return 0
    
    def open_trade(self, amount, direction, instrument, leverage, wallet, 
                   take_profit=None, stop_loss=None):
        """Открыть сделку"""
        try:
            data = {
                "amount": amount,
                "direction": direction,
                "instrument": instrument,
                "leverage": leverage,
                "wallet": wallet,
                "take_profit_price": take_profit,
                "stop_loss_price": stop_loss
            }
            
            response = requests.post(
                f"{self.base_url}/trades",
                headers=self.headers,
                json=data,
                timeout=REQUEST_TIMEOUT
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Ошибка открытия сделки: {e}")
            return None
    
    def close_trade(self, trade_id):
        """Закрыть сделку"""
        try:
            response = requests.post(
                f"{self.base_url}/trades/{trade_id}/close",
                headers=self.headers,
                json={},  # Пустое тело как в примере
                timeout=REQUEST_TIMEOUT
            )
            
            print(f"🔧 Статус закрытия: {response.status_code}")
            if response.status_code != 200:
                print(f"🔧 Ответ сервера: {response.text}")
            
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"❌ Ошибка закрытия сделки: {e}")
            return None
