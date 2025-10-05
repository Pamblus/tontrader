import time
import json
from datetime import datetime
from api import TradingAPI
from ai import AITrader
from config import UPDATE_INTERVAL, DEFAULT_WALLET, HISTORY_COUNT

class TradingBot:
    def __init__(self):
        self.api = TradingAPI()
        self.ai = AITrader()
        self.stats = {
            'total_trades': 0,
            'profit_trades': 0,
            'loss_trades': 0,
            'total_profit': 0,
            'active_trades': []
        }
    
    def get_market_data(self):
        """Сбор всех данных"""
        session = self.api.get_session()
        instruments = self.api.get_instruments()
        
        # Получаем ВСЕ сделки с реальным PnL
        all_trades = self.api.get_all_trades_with_profit(DEFAULT_WALLET)
        active_trades = [t for t in all_trades if t.get('status') == 'active']
        closed_trades = [t for t in all_trades if t.get('status') == 'closed']
        
        # Получаем ДЕТАЛЬНУЮ историю цен для ВСЕХ инструментов
        detailed_instruments = []
        price_history = {}
        
        for instrument in instruments:
            symbol = instrument['symbol']
            history = self.api.get_price_history(symbol, HISTORY_COUNT)
            
            # Добавляем текущую цену и детали инструмента
            instrument_data = {
                'symbol': symbol,
                'alias': instrument.get('alias', ''),
                'current_rate': instrument.get('rate', ''),
                'ask': instrument.get('ask', ''),
                'bid': instrument.get('bid', ''),
                'change_percent': instrument.get('profit_day_pl_percent', ''),
                'is_trading_open': instrument.get('is_trading_open', False)
            }
            detailed_instruments.append(instrument_data)
            
            if history and 'history' in history:
                recent_prices = history['history'][-20:]
                price_history[symbol] = recent_prices
                
                # Анализ тренда
                if len(recent_prices) >= 5:
                    first_price = float(recent_prices[0]['c'])
                    last_price = float(recent_prices[-1]['c'])
                    trend = "📈 ВОСХОДЯЩИЙ" if last_price > first_price else "📉 НИСХОДЯЩИЙ" if last_price < first_price else "➡️ БОКОВОЙ"
                    instrument_data['trend'] = trend
                    instrument_data['trend_strength'] = abs((last_price - first_price) / first_price * 100)
        
        # Форматируем активные сделки с РЕАЛЬНЫМ PnL
        formatted_active_trades = []
        for trade in active_trades:
            current_profit = trade.get('current_profit', 0)
            profit_percent = (current_profit / float(trade['amount'])) * 100 if float(trade['amount']) > 0 else 0
            
            formatted_trade = {
                'id': trade['id'],
                'instrument': trade['instrument'],
                'direction': trade['direction'],
                'amount': trade['amount'],
                'leverage': trade['leverage'],
                'open_rate': trade['open_rate'],
                'opened_at': trade['opened_at'],
                'status': trade['status'],
                'current_profit': current_profit,
                'profit_percent': profit_percent,
                'profit_status': "ПРИБЫЛЬ" if current_profit > 0 else "УБЫТОК" if current_profit < 0 else "БЕЗ ИЗМЕНЕНИЙ"
            }
            formatted_active_trades.append(formatted_trade)
        
        # Статистика по закрытым сделкам
        total_closed_profit = sum(float(t.get('profit', 0)) for t in closed_trades)
        profitable_closed = len([t for t in closed_trades if float(t.get('profit', 0)) > 0])
        losing_closed = len([t for t in closed_trades if float(t.get('profit', 0)) < 0])
        
        market_data = {
            'timestamp': datetime.now().isoformat(),
            'balance': session.get('balance', []) if session else [],
            'instruments': detailed_instruments,
            'price_history': price_history,
            'active_trades': formatted_active_trades,  # С реальным PnL!
            'closed_trades_stats': {
                'total_count': len(closed_trades),
                'profitable_count': profitable_closed,
                'losing_count': losing_closed,
                'total_profit': total_closed_profit
            },
            'user_balance': session.get('miner', {}) if session else {},
            'available_wallet': DEFAULT_WALLET
        }
        
        return market_data
    
    def format_ai_prompt(self, market_data):
        """Формирование промпта для ИИ с РЕАЛЬНЫМ PnL"""
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            prompt = f.read()
        
        # Форматируем данные инструментов с ценами
        instruments_info = []
        for inst in market_data['instruments']:
            trend_info = f", {inst.get('trend', '')} ({inst.get('trend_strength', 0):.2f}%)" if inst.get('trend') else ""
            instruments_info.append(
                f"{inst['symbol']} ({inst['alias']}): {inst['current_rate']} "
                f"(ask: {inst['ask']}, bid: {inst['bid']}){trend_info}"
            )
        
        # Форматируем активные сделки с РЕАЛЬНЫМ PnL
        active_trades_info = []
        for trade in market_data['active_trades']:
            profit_icon = "🟢" if trade['current_profit'] > 0 else "🔴" if trade['current_profit'] < 0 else "⚪"
            profit_color = "+" if trade['current_profit'] > 0 else ""
            
            active_trades_info.append(
                f"{profit_icon} ID: {trade['id']} | {trade['instrument']} {trade['direction'].upper()} | "
                f"${trade['amount']} x{trade['leverage']} | "
                f"PnL: {profit_color}${trade['current_profit']:.2f} ({profit_color}{trade['profit_percent']:.1f}%) | "
                f"Статус: {trade['profit_status']}"
            )
        
        # Статистика закрытых сделок
        closed_stats = market_data['closed_trades_stats']
        closed_trades_info = (
            f"Всего: {closed_stats['total_count']} | "
            f"Прибыльных: {closed_stats['profitable_count']} | "
            f"Убыточных: {closed_stats['losing_count']} | "
            f"Общий PnL: {closed_stats['total_profit']:.2f}$"
        )
        
        current_data = f"""
🎯 РЕАЛЬНЫЕ ДАННЫЕ СДЕЛОК на {market_data['timestamp']}:

💰 БАЛАНС КОШЕЛЬКОВ:
{json.dumps(market_data['balance'], indent=2, ensure_ascii=False)}

📊 ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
{chr(10).join(instruments_info)}

💹 АКТИВНЫЕ СДЕЛКИ ({len(market_data['active_trades'])}) - РЕАЛЬНЫЙ PnL:
{chr(10).join(active_trades_info) if active_trades_info else 'Нет активных сделок'}

📈 ИСТОРИЯ ЗАКРЫТЫХ СДЕЛОК:
{closed_trades_info}

Доступный кошелек: {market_data['available_wallet']}

ПРИМИ ОБОСНОВАННОЕ РЕШЕНИЕ:
"""
        
        return prompt + current_data
    
    def execute_ai_commands(self, commands, market_data):
        """Выполнение команд от ИИ с учетом PnL"""
        action = commands.get('action')
        comment = commands.get('comment', '')
        
        print(f"\n🤖 Коммент нейросети: {comment}")
        
        if action == 'open':
            instrument = commands.get('instrument')
            direction = commands.get('direction')
            amount = commands.get('amount')
            leverage = commands.get('leverage')
            
            if all([instrument, direction, amount, leverage]):
                instrument_exists = any(inst['symbol'] == instrument for inst in market_data['instruments'])
                if not instrument_exists:
                    print(f"❌ Инструмент {instrument} не найден!")
                    return
                
                result = self.api.open_trade(
                    amount=float(amount),
                    direction=direction,
                    instrument=instrument,
                    leverage=int(leverage),
                    wallet=DEFAULT_WALLET
                )
                
                if result and 'trade' in result:
                    trade = result['trade']
                    print(f"✅ ОТКРЫТА СДЕЛКА: {instrument} {direction} ${amount} x{leverage} (ID: {trade['id']})")
                    self.stats['total_trades'] += 1
                else:
                    print(f"❌ Ошибка открытия сделки")
        
        elif action == 'close':
            trade_id = commands.get('close_trade')
            if trade_id:
                active_trade_ids = [str(trade['id']) for trade in market_data['active_trades']]
                if trade_id not in active_trade_ids:
                    print(f"❌ Сделка {trade_id} не найдена или не активна!")
                    return
                
                # Находим сделку для отображения PnL
                closing_trade = next((t for t in market_data['active_trades'] if str(t['id']) == trade_id), None)
                if closing_trade:
                    print(f"🔒 ЗАКРЫВАЕМ СДЕЛКУ: ID {trade_id}")
                    print(f"   Инструмент: {closing_trade['instrument']}")
                    print(f"   Направление: {closing_trade['direction']}")
                    print(f"   Итоговый PnL: {closing_trade['current_profit']:.2f}$ ({closing_trade['profit_percent']:.1f}%)")
                
                result = self.api.close_trade(trade_id)
                if result:
                    print(f"✅ СДЕЛКА ЗАКРЫТА УСПЕШНО!")
                else:
                    print(f"❌ Ошибка закрытия сделки {trade_id}")
        
        elif action == 'wait':
            print(f"⏳ ОЖИДАНИЕ: {comment}")
        
        else:
            print(f"⚠️  Неизвестное действие: {action}")
    
    def print_status(self, market_data, commands):
        """Вывод статуса в консоль с PnL"""
        print("\n" + "="*70)
        print(f"🕒 Время: {datetime.now().strftime('%H:%M:%S')}")
        
        # Баланс
        balance_str = ""
        for bal in market_data['balance']:
            balance_str += f"{bal['wallet']}: ${bal['amount']} "
        print(f"💰 Баланс: {balance_str.strip()}")
        
        # Активные сделки с PnL
        print(f"🔧 Активные сделки: {len(market_data['active_trades'])}")
        for trade in market_data['active_trades']:
            profit_icon = "🟢" if trade['current_profit'] > 0 else "🔴" if trade['current_profit'] < 0 else "⚪"
            profit_sign = "+" if trade['current_profit'] > 0 else ""
            print(f"   {profit_icon} ID: {trade['id']} | {trade['instrument']} {trade['direction']} | "
                  f"PnL: {profit_sign}{trade['current_profit']:.2f}$ ({profit_sign}{trade['profit_percent']:.1f}%)")
        
        # Действие ИИ
        action = commands.get('action', 'wait')
        if action == 'open':
            print(f"🎯 Действие: ОТКРЫТИЕ {commands.get('instrument')}")
        elif action == 'close':
            print(f"🎯 Действие: ЗАКРЫТИЕ {commands.get('close_trade')}")
        else:
            print(f"🎯 Действие: ОЖИДАНИЕ")
        
        print("="*70)
    
    def run(self):
        """Основной цикл работы"""
        print("🚀 Запуск AI Трейдера...")
        print("📊 Теперь ИИ видит прибыль/убыток по сделкам!")
        
        while True:
            try:
                market_data = self.get_market_data()
                prompt = self.format_ai_prompt(market_data)
                
                ai_response = self.ai.call_ai([{"role": "user", "content": prompt}])
                print(f"🧠 Ответ ИИ: {ai_response}")
                
                commands = self.ai.parse_ai_response(ai_response)
                self.print_status(market_data, commands)
                self.execute_ai_commands(commands, market_data)
                
                print(f"\n⏰ Ожидание {UPDATE_INTERVAL} секунд...")
                time.sleep(UPDATE_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n🛑 Остановка бота...")
                break
            except Exception as e:
                print(f"❌ Ошибка в основном цикле: {e}")
                time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
