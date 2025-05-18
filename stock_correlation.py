import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
# from tigeropen.tiger_open_config import TigerOpenConfig
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Language, Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 对于 macOS
plt.rcParams['axes.unicode_minus'] = False

# 老虎证券API配置
def get_client_config():
    """
    https://quant.itigerup.com/#developer 开发者信息获取
    """
    client_config = TigerOpenClientConfig()
    # 使用绝对路径读取私钥文件
    current_dir = os.path.dirname(os.path.abspath("./tiger-test"))
    private_key_path = os.path.join(current_dir, 'keys', 'private.pem')
    client_config.private_key = read_private_key(private_key_path)
    client_config.tiger_id = '20153826'
    # client_config.account = '20240803144534965'
    client_config.account = '498843'
    client_config.language = Language.zh_CN  #可选，不填默认为英语'
    # client_config.timezone = 'US/Eastern' # 可选时区设置
    return client_config

client_config = get_client_config()

# 初始化行情客户端
quote_client = QuoteClient(client_config)

# 获取数据
end_date = datetime.now()
start_date = end_date - timedelta(days=252)  # 1年数据

# 获取富时中国A50指数数据
a50_symbol = 'JK8.SI'  # 富时中国A50指数的代码
print(f"正在获取 {a50_symbol} 的数据...")
a50_data = quote_client.get_bars(
    symbols=[a50_symbol],
    period='day',
    begin_time=int(start_date.timestamp() * 1000),
    end_time=int(end_date.timestamp() * 1000)
)

# 获取上证指数数据
sh_symbol = '000001.SH'  # 上证指数的代码
print(f"正在获取 {sh_symbol} 的数据...")
sh_data = quote_client.get_bars(
    symbols=[sh_symbol],
    period='day',
    begin_time=int(start_date.timestamp() * 1000),
    end_time=int(end_date.timestamp() * 1000)
)

# if not a50_data or not sh_data:
#     print("\n尝试获取可用的指数列表...")
#     indices = quote_client.get_symbol_names(market=Market.CN)
#     print("\n可用的指数列表：")
#     for idx in indices:
#         print(f"代码: {idx[0]}, 名称: {idx[1]}")

# 转换为DataFrame
a50_df = pd.DataFrame(a50_data)
sh_df = pd.DataFrame(sh_data)

# 设置日期索引
a50_df.index = pd.to_datetime(a50_df['time'], unit='ms')
sh_df.index = pd.to_datetime(sh_df['time'], unit='ms')

# 只保留需要的列
a50_df = a50_df[['close']]
sh_df = sh_df[['close']]

# 重命名列
a50_df.columns = ['A50']
sh_df.columns = ['SH']

# 合并数据，使用外连接确保包含所有日期
merged_df = pd.merge(a50_df, sh_df, left_index=True, right_index=True, how='outer')

# 删除任何包含NaN的行
merged_df = merged_df.dropna()

print(f"\n数据对齐后的记录数: {len(merged_df)}")

# 计算每日收益率
returns_df = merged_df.pct_change().dropna()

# 计算相关性
correlation = returns_df['A50'].corr(returns_df['SH'])

# 创建图表
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# 绘制价格走势对比图（使用双Y轴）
ax1_twin = ax1.twinx()

# 绘制A50指数（左Y轴）
line1 = ax1.plot(merged_df.index, merged_df['A50'], label='富时中国A50', color='blue')
ax1.set_ylabel('富时中国A50指数', color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

# 绘制上证指数（右Y轴）
line2 = ax1_twin.plot(merged_df.index, merged_df['SH'], label='上证指数', color='red')
ax1_twin.set_ylabel('上证指数', color='red')
ax1_twin.tick_params(axis='y', labelcolor='red')

# 添加图例
lines = line1 + line2
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left')

ax1.set_title('富时中国A50与上证指数价格走势对比')
ax1.grid(True)

# 绘制相关性散点图
ax2.scatter(returns_df['A50'], returns_df['SH'], alpha=0.5)
ax2.set_title(f'收益率相关性散点图 (相关系数: {correlation:.4f})')
ax2.set_xlabel('富时中国A50收益率')
ax2.set_ylabel('上证指数收益率')
ax2.grid(True)

# 调整布局
plt.tight_layout()

# 保存图表
plt.savefig('stock_correlation.png')
plt.close()

print(f'\n富时中国A50与上证指数的相关系数: {correlation:.4f}') 