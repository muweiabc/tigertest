import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OKXTrading:
    def __init__(self):
        # Initialize OKX exchange
        self.exchange = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_SECRET_KEY'),
            'password': os.getenv('OKX_PASSPHRASE'),
            'enableRateLimit': True,
        })

    def get_account_balance(self):
        """获取账户余额信息"""
        try:
            balance = self.exchange.fetch_balance()
            # 只显示非零余额
            non_zero_balances = {
                currency: amount
                for currency, amount in balance['total'].items()
                if amount > 0
            }
            return non_zero_balances
        except Exception as e:
            print(f"获取账户余额时出错: {str(e)}")
            return None

    def get_trading_history(self, symbol='BTC/USDT', limit=10):
        """获取交易历史"""
        try:
            trades = self.exchange.fetch_my_trades(symbol, limit=limit)
            if trades:
                df = pd.DataFrame(trades)
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df[['datetime', 'side', 'price', 'amount', 'cost']]
            return None
        except Exception as e:
            print(f"获取交易历史时出错: {str(e)}")
            return None

    def get_open_orders(self, symbol='BTC/USDT'):
        """获取当前未完成的订单"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            if orders:
                df = pd.DataFrame(orders)
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df[['datetime', 'side', 'price', 'amount', 'status']]
            return None
        except Exception as e:
            print(f"获取未完成订单时出错: {str(e)}")
            return None

    def get_order_book(self, symbol='BTC/USDT', limit=5):
        """获取订单簿信息"""
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit)
            bids_df = pd.DataFrame(order_book['bids'], columns=['price', 'amount'])
            asks_df = pd.DataFrame(order_book['asks'], columns=['price', 'amount'])
            return {
                'bids': bids_df,
                'asks': asks_df
            }
        except Exception as e:
            print(f"获取订单簿时出错: {str(e)}")
            return None

def main():
    # 创建OKX交易实例
    okx = OKXTrading()

    # 获取账户余额
    print("\n=== 账户余额 ===")
    balance = okx.get_account_balance()
    if balance:
        for currency, amount in balance.items():
            print(f"{currency}: {amount}")

    # 获取交易历史
    print("\n=== 最近交易历史 ===")
    trades = okx.get_trading_history()
    if trades is not None:
        print(trades)

    # 获取未完成订单
    print("\n=== 未完成订单 ===")
    open_orders = okx.get_open_orders()
    if open_orders is not None:
        print(open_orders)

    # 获取订单簿
    print("\n=== 订单簿信息 ===")
    order_book = okx.get_order_book()
    if order_book:
        print("\n买单:")
        print(order_book['bids'])
        print("\n卖单:")
        print(order_book['asks'])

if __name__ == "__main__":
    main() 