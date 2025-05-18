from tigeropen.quote.quote_client import QuoteClient
from tigeropen.common.consts import Language, Market
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
import os
import pandas as pd
from datetime import datetime

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
    client_config.account = '498843'
    client_config.language = Language.zh_CN
    return client_config

def get_all_symbols():
    # 初始化客户端
    client_config = get_client_config()
    quote_client = QuoteClient(client_config)
    
    # 获取所有市场列表
    markets = [
        Market.US,      # 美股
        Market.HK,      # 港股
        Market.CN,      # A股
        Market.SG,      # 新加坡
    ]
    
    all_symbols = []
    # symbol_names = quote_client.get_symbol_names(market=Market.ALL)
    # print(symbol_names)
    # 遍历每个市场获取证券信息
    for market in markets:
        try:
            print(f"正在获取 {market.value} 市场的证券信息...")
            # 获取该市场的所有证券信息
            symbols = quote_client.get_symbol_names(market=market.value)
            
            if not symbols:
                print(f"未获取到 {market.value} 市场的证券信息")
                continue
                
            # 将每个证券的信息添加到列表中
            for symbol in symbols:
                try:
                    symbol_info = {
                        'market': market.value,
                        'symbol': symbol[0],
                        'name': symbol[1],
                        # 'currency': symbol.currency,
                        # 'exchange': symbol.exchange,
                        # 'type': symbol.type,
                        # 'status': symbol.status,
                        # 'description': symbol.description
                    }
                    all_symbols.append(symbol_info)
                except AttributeError as e:
                    print(f"处理证券信息时出错: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"获取 {market.value} 市场信息时出错: {str(e)}")
            continue
    
    if not all_symbols:
        print("未获取到任何证券信息")
        return
        
    # 转换为DataFrame
    df = pd.DataFrame(all_symbols)
    
    # 生成文件名（包含时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'tiger_symbols_{timestamp}.csv'
    
    # 保存到CSV文件
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n证券信息已保存到文件: {filename}")
    print(f"总共获取到 {len(df)} 个证券信息")
    
    # 打印每个市场的证券数量统计
    market_stats = df.groupby('market').size()
    print("\n各市场证券数量统计:")
    print(market_stats)

if __name__ == "__main__":
    get_all_symbols() 