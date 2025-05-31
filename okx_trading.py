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
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_api_credentials(is_simulated=True):
    """
    从环境变量获取API凭证
    :param is_simulated: 是否为模拟交易
    :return: (api_key, secret_key, passphrase)
    """
    if is_simulated:
        api_key = os.getenv('OKX_SIM_apikey')
        secret_key = os.getenv('OKX_SIM_secretkey')
        passphrase = os.getenv('OKX_SIM_PASSPHRASE')
        logger.info("使用模拟交易API凭证")
    else:
        api_key = os.getenv('OKX_API_KEY')
        secret_key = os.getenv('OKX_SECRET_KEY')
        passphrase = os.getenv('OKX_PASSPHRASE')
        logger.info("使用真实交易API凭证")
    
    if not all([api_key, secret_key, passphrase]):
        raise ValueError("请在.env文件中设置正确的API凭证信息")
    
    return api_key, secret_key, passphrase

def format_json_response(response):
    """格式化API响应为JSON字符串"""
    try:
        if isinstance(response, dict):
            return json.dumps(response, indent=2, ensure_ascii=False)
        elif hasattr(response, 'data'):
            return json.dumps(response.data, indent=2, ensure_ascii=False)
        else:
            return str(response)
    except Exception as e:
        logger.error(f"格式化JSON响应时出错: {str(e)}")
        return str(response)

class OKXTrading:
    def __init__(self, is_simulated=True):
        """
        初始化OKX交易类
        :param is_simulated: 是否为模拟交易
        """
        self.flag = "1" if is_simulated else "0"  # 1: 模拟盘, 0: 实盘
        self.max_retries = 3
        self.retry_delay = 2  # 重试延迟秒数
        
        # 获取API凭证
        api_key, secret_key, passphrase = get_api_credentials(is_simulated)
        
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

    def get_account_balance(self, ccy=None):
        logger.info("获取账户余额信息")
        """
        获取账户余额信息
        :param ccy: 币种，如 'BTC', 'ETH', 'USDT'，不传则返回所有币种
        """
        try:
            params = {}
            if ccy:
                params['ccy'] = ccy
            balance_response = self._make_request(self.accountAPI.get_account_balance, **params)
            if balance_response and 'data' in balance_response and balance_response['data']:
                account_data = balance_response['data'][0]
                logger.info(f"账户总权益: {account_data['totalEq']} USDT")
                logger.info(f"账户可用余额: {account_data['availEq']} USDT")
            
                # 显示各个币种的余额
                logger.info("\n各币种余额详情:")
                for balance in account_data['details']:
                    ccy = balance['ccy']
                    eq = balance['eq']
                    avail_eq = balance['availEq']
                    if float(eq) > 0 or float(avail_eq) > 0:  # 只显示有余额的币种
                        logger.info(f"{ccy}:")
                        logger.info(f"  总余额: {eq} {ccy}")
                        logger.info(f"  可用余额: {avail_eq} {ccy}")
            return balance_response
        except Exception as e:
            logger.error(f"获取账户余额时出错: {str(e)}")
            return None

    def get_account_positions(self, instType=None, instId=None):
        """
        获取账户持仓信息
        :param instType: 产品类型，可选值：SPOT(现货), MARGIN(杠杆), SWAP(永续合约), FUTURES(交割合约), OPTION(期权)
        """
        try:
            params = {}
            if instType:
                params['instType'] = instType
            if instId:
                params['instId'] = instId
            return self._make_request(self.accountAPI.get_positions, **params)
        except Exception as e:
            logger.error(f"获取持仓信息时出错: {str(e)}")
            return None

    def get_account_config(self, instType=None):
        """
        获取账户配置信息
        :param instType: 产品类型，可选值：SPOT(现货), MARGIN(杠杆), SWAP(永续合约), FUTURES(交割合约), OPTION(期权)
        """
        try:
            params = {}
            if instType:
                params['instType'] = instType
            return self._make_request(self.accountAPI.get_account_config, **params)
        except Exception as e:
            logger.error(f"获取账户配置时出错: {str(e)}")
            return None

    def get_trading_history(self, symbol='ETH-USDT', limit=10):
        """获取交易历史"""
        try:
            params = {
                'instType': 'SPOT',
                'instId': symbol,
                'limit': str(limit)
            }
            return self._make_request(self.tradeAPI.get_orders_history, **params)
        except Exception as e:
            logger.error(f"获取交易历史时出错: {str(e)}")
            return None

    def get_open_orders(self, symbol='ETH-USDT'):
        """获取当前未完成的订单"""
        params = {
            'instType': 'SPOT',
            'instId': symbol
        }
        orders = self._make_request(self.tradeAPI.get_order_list, **params)
        order_list = []
        for order in orders['data']:
            order_info = {
                '订单ID': order['ordId'],
                '交易对': order['instId'],
                '方向': '买入' if order['side'] == 'buy' else '卖出',
                '价格': order['px'],
                '数量': order['sz'],
                '状态': order['state'],
                '创建时间': order['cTime']
            }
            order_list.append(order_info)
            logger.info(f"订单信息: {order_info}")
        return orders
    
    def cancel_all_orders(self):
        """取消所有未完成的订单"""
        open_orders = self.get_open_orders()
        if open_orders and 'data' in open_orders and open_orders['data']:
            for order in open_orders['data']:
                self.tradeAPI.cancel_order(
                    instId=order['instId'],
                    ordId=order['ordId']
                )
        logger.info("已取消所有未完成订单")

    def get_order_book(self, symbol='ETH-USDT', limit=5):
        """获取订单簿信息"""
        try:
            params = {
                'instId': symbol,
                'sz': str(limit)
            }
            return self._make_request(self.marketAPI.get_books, **params)
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
        trader = OKXTrading(is_simulated=False)
        
        # # 获取所有币种余额
        # logger.info("\n=== 所有币种余额 ===")
        # all_balance = trader.get_account_balance()
        # logger.info(format_json_response(all_balance))
        
        # # 获取USDT余额
        # logger.info("\n=== USDT余额 ===")
        # usdt_balance = trader.get_account_balance(ccy='USDT')
        # logger.info(format_json_response(usdt_balance))
        
        # # 获取账户配置
        # logger.info("\n=== 账户配置 ===")
        # account_config = trader.get_account_config()
        # logger.info(format_json_response(account_config))
        
        # # 获取所有持仓
        # logger.info("\n=== 所有持仓 ===")
        # all_positions = trader.get_account_positions()
        # logger.info(format_json_response(all_positions))
        
        # 获取现货持仓
        logger.info("\n=== 现货持仓 ===")
        spot_positions = trader.get_account_positions(instType='SWAP', instId='ETH-USDT-SWAP')
        logger.info(format_json_response(spot_positions))
        
        # 获取ETH现货持仓
        logger.info("\n=== ETH现货持仓 ===")
        eth_positions = trader.get_account_positions(instType='SWAP', instId='ETH-USDT-SWAP')
        logger.info(format_json_response(eth_positions))

    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    # okx交易api需要翻墙
    main() 