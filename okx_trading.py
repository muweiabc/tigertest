import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import okx.Account as Account
import okx.Trade as Trade
import okx.MarketData as MarketData
import time
import requests
from requests.exceptions import RequestException
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class OKXTrading:
    def __init__(self, api_key, secret_key, passphrase, is_simulated=True):
        self.flag = "1" if is_simulated else "0"  # 1: 模拟盘, 0: 实盘
        self.max_retries = 3
        self.retry_delay = 2  # 重试延迟秒数
        
        # 配置API客户端
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, self.flag)
        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, self.flag, debug=True)
        self.marketAPI = MarketData.MarketAPI(api_key, secret_key, passphrase, False, self.flag)
        
        # 设置请求超时
        self.timeout = 10

    def _make_request(self, func, *args, **kwargs):
        """通用请求处理函数，包含重试机制"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except RequestException as e:
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"达到最大重试次数，请求失败: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"发生未知错误: {str(e)}")
                raise

    def get_positions(self):
        """获取所有持仓信息"""
        return self._make_request(self.accountAPI.get_positions)

    def get_eth_position(self):
        """获取ETH持仓信息"""
        return self._make_request(self.accountAPI.get_positions, instId="ETH-USDT")

    def get_eth_price(self):
        """获取ETH当前价格"""
        return self._make_request(self.marketAPI.get_ticker, instId="ETH-USDT")

    def place_eth_order(self, side, size, price=None):
        """
        下单ETH
        :param side: 'buy' 或 'sell'
        :param size: 数量
        :param price: 价格（市价单可不传）
        """
        params = {
            "instId": "ETH-USDT",
            "tdMode": "cash",  # 现货交易
            "side": side,
            "ordType": "limit" if price else "market",
            "sz": str(size)
        }
        if price:
            params["px"] = str(price)
        
        return self._make_request(self.tradeAPI.place_order, **params)

    def get_account_balance(self):
        """获取账户余额信息"""
        try:
            return self._make_request(self.accountAPI.get_account_balance)
        except Exception as e:
            logger.error(f"获取账户余额时出错: {str(e)}")
            return None

    def get_trading_history(self, symbol='ETH-USDT', limit=10):
        """获取交易历史"""
        try:
            return self._make_request(self.tradeAPI.get_orders_history,  instId=symbol, limit=str(limit))
        except Exception as e:
            logger.error(f"获取交易历史时出错: {str(e)}")
            return None

    def get_open_orders(self, symbol='ETH-USDT'):
        """获取当前未完成的订单"""
        try:
            return self._make_request(self.tradeAPI.get_orders_pending, instId=symbol)
        except Exception as e:
            logger.error(f"获取未完成订单时出错: {str(e)}")
            return None

    def get_order_book(self, symbol='ETH-USDT', limit=5):
        """获取订单簿信息"""
        try:
            return self._make_request(self.marketAPI.get_books, instId=symbol, sz=str(limit))
        except Exception as e:
            logger.error(f"获取订单簿时出错: {str(e)}")
            return None

def main():
    try:
        # 从环境变量加载API配置
        api_key = os.getenv('OKX_API_KEY')
        secret_key = os.getenv('OKX_SECRET_KEY')
        passphrase = os.getenv('OKX_PASSPHRASE')
        
        if not all([api_key, secret_key, passphrase]):
            logger.error("错误：请在.env文件中设置OKX_API_KEY, OKX_SECRET_KEY和OKX_PASSPHRASE")
            return
        
        # 初始化交易类
        trader = OKXTrading(api_key, secret_key, passphrase, is_simulated=True)
        
        # 获取ETH价格
        price_info = trader.get_eth_price()
        logger.info(f"ETH当前价格: {price_info}")
        
        # 获取ETH持仓
        position_info = trader.get_eth_position()
        logger.info(f"ETH持仓信息: {position_info}")
        
        # 获取账户余额
        logger.info("\n=== 账户余额 ===")
        balance = trader.get_account_balance()
        if balance:
            logger.info(balance)

        # 获取交易历史
        logger.info("\n=== 最近交易历史 ===")
        trades = trader.get_trading_history()
        if trades is not None:
            logger.info(trades)

        # 获取未完成订单
        logger.info("\n=== 未完成订单 ===")
        open_orders = trader.get_open_orders()
        if open_orders is not None:
            logger.info(open_orders)

        # 获取订单簿
        logger.info("\n=== 订单簿信息 ===")
        order_book = trader.get_order_book()
        if order_book:
            logger.info("\n买单:")
            logger.info(order_book['bids'])
            logger.info("\n卖单:")
            logger.info(order_book['asks'])

    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    # okx交易api需要翻墙
    main() 