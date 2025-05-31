import time
import logging
from okx_trading import OKXTrading
import numpy as np
import requests
from requests.exceptions import RequestException
import backoff
import json

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OKXGridTrader(OKXTrading):
    def __init__(self, is_simulated=True):
        super().__init__(is_simulated=is_simulated)
        self.grid_orders = []
        self.is_running = False
        
    def calculate_grid_levels(self, upper_price, lower_price, num_grids):
        """
        计算网格价格水平
        :param upper_price: 网格上限价格
        :param lower_price: 网格下限价格
        :param num_grids: 网格数量
        :return: 网格价格列表
        """
        return np.linspace(lower_price, upper_price, num_grids)
    
    def calculate_grid_quantity(self, total_investment, grid_prices):
        """
        计算每个网格的投资数量
        :param total_investment: 总投资金额(USDT)
        :param grid_prices: 网格价格列表
        :return: 每个网格的ETH数量
        """
        # 平均分配投资金额到每个网格
        investment_per_grid = total_investment / len(grid_prices)
        # 计算每个网格的ETH数量
        quantities = [investment_per_grid / price for price in grid_prices]
        return quantities
    
    def place_grid_orders(self, upper_price, lower_price, num_grids, total_investment):
        """
        放置网格订单
        :param upper_price: 网格上限价格
        :param lower_price: 网格下限价格
        :param num_grids: 网格数量
        :param total_investment: 总投资金额(USDT)
        """
        # 获取当前价格
        price_response = self.get_eth_price()
        current_price = float(price_response['data'][0]['last'])
        
        # 计算网格价格水平
        grid_prices = self.calculate_grid_levels(upper_price, lower_price, num_grids)
        
        # 计算每个网格的数量
        quantities = self.calculate_grid_quantity(total_investment, grid_prices)
        
        # 取消所有现有订单
        self.cancel_all_orders()
        
        # 放置网格订单
        for i in range(len(grid_prices)):
            price = grid_prices[i]
            quantity = quantities[i]
            
            if price < current_price:
                # 当前价格以下放置买单
                order = self.place_eth_order('buy', quantity, price)
                logger.info(f"放置买单: 价格={price}, 数量={quantity}")
            else:
                # 当前价格以上放置卖单
                order = self.place_eth_order('sell', quantity, price)
                logger.info(f"放置卖单: 价格={price}, 数量={quantity}")
            
            self.grid_orders.append(order)
            
        logger.info(f"网格订单放置完成，共{len(grid_prices)}个网格")
    
    def cancel_all_orders(self):
        """取消所有未完成的订单"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                open_orders = self.get_open_orders()
                if open_orders and 'data' in open_orders and open_orders['data']:
                    for order in open_orders['data']:
                        try:
                            self.tradeAPI.cancel_order(
                                instId=order['instId'],
                                ordId=order['ordId']
                            )
                        except Exception as e:
                            logger.error(f"取消订单 {order['ordId']} 失败: {str(e)}")
                            continue
                logger.info("已取消所有未完成订单")
                return
            except Exception as e:
                logger.error(f"获取未完成订单失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("获取未完成订单失败，取消操作终止")
                    return
                time.sleep(retry_delay)
    
    def get_existing_orders(self):
        """
        查询现有订单信息
        :return: 订单信息列表
        """
        orders = self.get_open_orders()
        if not orders or 'data' not in orders or not orders['data']:
            logger.info("当前没有未完成的订单")
            return []
            
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
            
        return order_list
    
    def start_grid_trading(self, upper_price, lower_price, num_grids, total_investment, check_interval=60):
        """
        启动网格交易
        :param upper_price: 网格上限价格
        :param lower_price: 网格下限价格
        :param num_grids: 网格数量
        :param total_investment: 总投资金额(USDT)
        :param check_interval: 检查间隔(秒)
        """
        self.is_running = True
        logger.info("启动网格交易...")
        
        # 初始放置网格订单
        self.place_grid_orders(upper_price, lower_price, num_grids, total_investment)
        
        flag = 1
        while self.is_running:
            # 检查订单状态并重新平衡网格
            logger.info(f"flag: {flag}")
            flag += 1   
            self.rebalance_grid()
            time.sleep(check_interval)
    
    def rebalance_grid(self):
        """重新平衡网格"""
        max_retries = 3
        retry_delay = 2
        
        # 获取当前持仓
        for attempt in range(max_retries):
            try:
                positions = self.get_eth_position()
                if positions and 'data' in positions and positions['data']:
                    break
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"获取持仓信息失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("获取持仓信息失败，跳过本次重平衡")
                    return
                time.sleep(retry_delay)
        
        # 获取当前价格
        for attempt in range(max_retries):
            try:
                price_response = self.get_eth_price()
                if price_response and 'data' in price_response and price_response['data']:
                    current_price = float(price_response['data'][0]['last'])
                    break
                time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"获取价格信息失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("获取价格信息失败，跳过本次重平衡")
                    return
                time.sleep(retry_delay)
        
        # 检查是否有成交的订单
        for attempt in range(max_retries):
            try:
                open_orders = self.get_open_orders()
                if not open_orders or 'data' not in open_orders or not open_orders['data']:
                    # 如果没有未完成订单，重新放置网格
                    try:
                        self.place_grid_orders(
                            upper_price=current_price * 1.05,  # 上限设为当前价格的105%
                            lower_price=current_price * 0.95,  # 下限设为当前价格的95%
                            num_grids=10,  # 默认10个网格
                            total_investment=1000  # 默认投资1000 USDT
                        )
                        logger.info("网格订单重新放置成功")
                    except Exception as e:
                        logger.error(f"重新放置网格订单失败: {str(e)}")
                break
            except Exception as e:
                logger.error(f"检查订单状态失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    logger.error("检查订单状态失败，跳过本次重平衡")
                    return
                time.sleep(retry_delay)
    
    def stop_grid_trading(self):
        """停止网格交易"""
        self.is_running = False
        self.cancel_all_orders()
        logger.info("网格交易已停止")



def send_feishu_alert(message):
    payload = {
        "msg_type": "text",
        "content": {"text": f"🚨 系统故障告警: {message}"}
    }
    webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/9863a7ef-72f9-44b4-bef9-13bc9d9d172c"
    response = requests.post(webhook, json=payload)
    return response.json()

    # 调用示例
    

def main():
    try:
        # 初始化网格交易类
        grid_trader = OKXGridTrader(is_simulated=True)
        
        # 查询账户余额
        logger.info("\n=== 账户余额信息 ===")
        balance_response = grid_trader.get_account_balance()
        
        
        # 获取当前ETH价格
        price_response = grid_trader.get_eth_price()
        current_price = float(price_response['data'][0]['last'])
        logger.info(f"\n当前ETH价格: {current_price} USDT")
        
        # 设置网格参数
        upper_price = current_price * 1.02  # 上限设为当前价格的110%
        lower_price = current_price * 0.98  # 下限设为当前价格的90%
        num_grids = 10  # 10个网格
        total_investment = 1000  # 投资1000 USDT
        
        logger.info(f"\n=== 网格交易参数 ===")
        logger.info(f"价格区间: {lower_price:.2f} - {upper_price:.2f} USDT")
        logger.info(f"网格数量: {num_grids}")
        logger.info(f"总投资额: {total_investment} USDT")
        
        # 启动网格交易
        grid_trader.start_grid_trading(
            upper_price=upper_price,
            lower_price=lower_price,
            num_grids=num_grids,
            total_investment=total_investment
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断，停止网格交易")
        grid_trader.stop_grid_trading()
    except Exception as e:
        logger.error(f"网格交易异常: {str(e)}")
        send_feishu_alert(f"网格交易异常: {str(e)}")


if __name__ == "__main__":
    main() 