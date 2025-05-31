from tigeropen.common.consts import Language, Market, BarPeriod, QuoteRight
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.trade.trade_client import TradeClient
import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GridTrading:
    def __init__(self, symbol, upper_price, lower_price, grid_num, quantity_per_grid, market=Market.HK):
        """
        初始化网格交易策略
        :param symbol: 交易标的代码
        :param upper_price: 网格上限价格
        :param lower_price: 网格下限价格
        :param grid_num: 网格数量
        :param quantity_per_grid: 每个网格的交易数量
        :param market: 市场类型，默认港股
        """
        self.symbol = symbol
        self.market = market
        self.upper_price = upper_price
        self.lower_price = lower_price
        self.grid_num = grid_num
        self.quantity_per_grid = quantity_per_grid
        self.grid_prices = np.linspace(lower_price, upper_price, grid_num + 1)
        self.positions = {}  # 记录每个网格的持仓状态
        self.trade_history = []  # 记录交易历史
        
        # 初始化API客户端
        self.client_config = self._get_client_config()
        self.quote_client = QuoteClient(self.client_config)
        self.trade_client = TradeClient(self.client_config)
        
        # 获取行情权限
        try:
            # 指定市场类型获取权限
            permissions = self.quote_client.grab_quote_permission(market=self.market)
            logger.info(f"获取行情权限成功: {permissions}")
            
            # 验证权限
            if not permissions or self.market not in permissions:
                raise ValueError(f"未获得{self.market}市场权限")
                
        except Exception as e:
            logger.error(f"获取行情权限失败: {e}")
            raise
        
    def _get_client_config(self):
        """获取API配置"""
        try:
            client_config = TigerOpenClientConfig()
            current_dir = os.path.dirname(os.path.abspath(__file__))
            private_key_path = os.path.join(current_dir, 'keys', 'private.pem')
            
            if not os.path.exists(private_key_path):
                raise FileNotFoundError(f"私钥文件不存在: {private_key_path}")
                
            client_config.private_key = read_private_key(private_key_path)
            client_config.tiger_id = '20153826'  # 替换为你的模拟账号ID
            client_config.account = '20240803144534965'  # 替换为你的模拟账号
            client_config.language = Language.zh_CN
            return client_config
        except Exception as e:
            logger.error(f"初始化配置失败: {e}")
            raise
    
    def get_current_price(self):
        """获取当前价格"""
        try:
            # 港股代码需要添加市场前缀
            full_symbol = f"{self.symbol}.HK" if self.market == Market.HK else self.symbol
            # 添加市场参数
            quote = self.quote_client.get_stock_briefs([full_symbol], market=self.market)
            
            if quote.empty:
                raise ValueError(f"无法获取股票 {full_symbol} 的行情数据")
                
            current_price = float(quote['last'].iloc[0])
            logger.info(f"获取当前价格成功: {current_price}")
            return current_price
        except Exception as e:
            logger.error(f"获取价格失败: {e}")
            return None
    
    def place_order(self, price, quantity, side):
        """下单函数"""
        try:
            # 港股代码需要添加市场前缀
            full_symbol = f"{self.symbol}.HK" if self.market == Market.HK else self.symbol
            
            order = self.trade_client.place_order(
                symbol=full_symbol,
                quantity=quantity,
                side=side,
                order_type='LIMIT',
                limit_price=price,
                market=self.market
            )
            
            trade_record = {
                'time': datetime.now(),
                'symbol': full_symbol,
                'price': price,
                'quantity': quantity,
                'side': side,
                'order_id': order.order_id
            }
            
            self.trade_history.append(trade_record)
            logger.info(f"下单成功: {trade_record}")
            return order
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return None
    
    def check_and_trade(self):
        """检查价格并执行交易"""
        current_price = self.get_current_price()
        if current_price is None:
            return
            
        logger.info(f"当前价格: {current_price}")
        
        # 找到当前价格所在的网格
        grid_index = np.searchsorted(self.grid_prices, current_price)
        
        # 如果价格在网格范围内
        if 0 < grid_index < len(self.grid_prices):
            grid_price = self.grid_prices[grid_index]
            
            # 如果价格突破网格，执行交易
            if current_price > grid_price and grid_index not in self.positions:
                # 买入
                order = self.place_order(current_price, self.quantity_per_grid, 'BUY')
                if order:
                    self.positions[grid_index] = True
                    logger.info(f"买入信号: 价格 {current_price}, 数量 {self.quantity_per_grid}")
            
            elif current_price < grid_price and grid_index in self.positions:
                # 卖出
                order = self.place_order(current_price, self.quantity_per_grid, 'SELL')
                if order:
                    del self.positions[grid_index]
                    logger.info(f"卖出信号: 价格 {current_price}, 数量 {self.quantity_per_grid}")
    
    def run(self, interval=60):
        """运行网格交易策略"""
        logger.info(f"开始运行网格交易策略 - 标的: {self.symbol}")
        logger.info(f"价格区间: {self.lower_price} - {self.upper_price}")
        logger.info(f"网格数量: {self.grid_num}")
        logger.info(f"每格数量: {self.quantity_per_grid}")
        logger.info(f"网格价格: {self.grid_prices}")
        
        try:
            while True:
                self.check_and_trade()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("策略已停止")
            self.print_trade_history()
        except Exception as e:
            logger.error(f"策略运行出错: {e}")
            self.print_trade_history()
    
    def print_trade_history(self):
        """打印交易历史"""
        if self.trade_history:
            df = pd.DataFrame(self.trade_history)
            logger.info("\n交易历史:")
            logger.info(f"\n{df}")
            
            # 计算总收益
            total_profit = 0
            for trade in self.trade_history:
                if trade['side'] == 'SELL':
                    total_profit += trade['price'] * trade['quantity']
                else:
                    total_profit -= trade['price'] * trade['quantity']
            logger.info(f"总收益: {total_profit:.2f}")
        else:
            logger.info("暂无交易记录")

if __name__ == "__main__":
    # 示例：创建一个网格交易策略
    strategy = GridTrading(
        symbol='03033',  # 港股代码
        upper_price=200,  # 上限价格
        lower_price=150,  # 下限价格
        grid_num=10,     # 10个网格
        quantity_per_grid=100,  # 每个网格交易100股
        market=Market.HK  # 港股市场
    )
    
    # 运行策略，每60秒检查一次
    strategy.run(interval=60) 