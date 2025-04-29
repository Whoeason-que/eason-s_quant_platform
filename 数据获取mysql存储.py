import pandas as pd
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import tushare as ts
import akshare as ak
from pathlib import Path
from typing import Optional, List, Dict, Literal, Union
import pymysql
import gc
import time

# 数据库配置
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '3321Whoeason',
    'database': 'quant_data',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

DEFAULT_QUANT_DIR = Path.home() / "Desktop" / "quant"
DEFAULT_YAML_PATH = DEFAULT_QUANT_DIR /"配置"/"stock_config.yaml"
MANIFEST_PATH = DEFAULT_QUANT_DIR /"配置"/ "manifest.yaml"

def get_stock_info() -> None:
    """获取股票基本信息并保存到MySQL"""
    try:
        pro = ts.pro_api()  # 初始化tushare pro接口
        df = pro.stock_basic(
            exchange='', 
            list_status='L', 
            fields='ts_code,symbol,name,list_date,industry'
        )
        def save_stock_info_to_mysql(df: pd.DataFrame) -> None:
            """将股票基本信息存储到MySQL"""
            if df.empty:
                print("没有股票基本信息需要存储")
                return
            
            try:
                connection = pymysql.connect(**db_config)
                with connection.cursor() as cursor:
                    # 检查表是否存在，如果不存在则创建
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS stock_info (
                            ts_code VARCHAR(20) PRIMARY KEY,
                            symbol VARCHAR(10),
                            name VARCHAR(50),
                            list_date DATE,
                            industry VARCHAR(50)
                        )
                    """)
                    connection.commit()

                    # 批量插入或更新数据
                    sql = """
                        INSERT INTO stock_info (ts_code, symbol, name, list_date, industry)
                        VALUES (%s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        symbol = VALUES(symbol),
                        name = VALUES(name),
                        list_date = VALUES(list_date),
                        industry = VALUES(industry)
                    """
                    data_tuples = [tuple(x) for x in df.to_records(index=False)]
                    cursor.executemany(sql, data_tuples)
                    connection.commit()
                    print(f"成功插入或更新 {len(df)} 条股票基本信息")
            except Exception as e:
                print(f"存储股票基本信息失败: {str(e)}")
                connection.rollback()
            finally:
                connection.close()
                # 将数据存储到MySQL
        save_stock_info_to_mysql(df)
        
        # 如果需要同时保存到CSV，可以保留以下代码
        # output_path = Path(output_path)
        # output_path.parent.mkdir(parents=True, exist_ok=True)
        # df.to_csv(output_path, index=False)
    except Exception as e:
        print(f"获取股票信息失败: {str(e)}")
        raise

def generate_yaml_config(
    yaml_path: Union[str, Path] = DEFAULT_YAML_PATH
) -> None:
    """生成YAML配置文件，数据源改为MySQL"""
    yaml_path = Path(yaml_path)
    def get_stock_info_from_mysql() -> pd.DataFrame:
        """从MySQL获取股票基本信息"""
        try:
            connection = pymysql.connect(**db_config)
            with connection.cursor() as cursor:
                sql = "SELECT ts_code, name, list_date, industry FROM stock_info"
                cursor.execute(sql)
                result = cursor.fetchall()
                
                # 转换为DataFrame
                if result:
                    df = pd.DataFrame(result)
                    # 将list_date转换为字符串格式
                    df['list_date'] = df['list_date'].astype(str)
                    return df
                else:
                    print("MySQL中没有股票信息")
                    return pd.DataFrame()
        except Exception as e:
            print(f"从MySQL获取股票信息失败: {str(e)}")
            return pd.DataFrame()
        finally:
            connection.close()
    try:
        # 从MySQL获取股票基本信息
        stock_info = get_stock_info_from_mysql()
        
        if stock_info.empty:
            print("没有股票信息，无法生成YAML配置文件")
            return
        
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {}
        for _, row in stock_info.iterrows():
            try:
                # 验证必要字段
                if pd.isna(row['ts_code']) or pd.isna(row['name']) or pd.isna(row['list_date']):
                    continue
                
                # 处理上市日期
                list_date = str(row['list_date']).replace("-", "")
                if not list_date.isdigit() or len(list_date) != 8:
                    print(f"无效上市日期: {row['name']} - {row['list_date']}")
                    continue
                def convert_code(code: str) -> str:
                    """统一股票代码格式"""
                    code = code.strip()
                    exchange_map = {
                        '.SH': 'sh',  # 上海证券交易所
                        '.SZ': 'sz',  # 深圳证券交易所
                        '.HK': 'hk',  # 香港交易所
                        '.BJ': 'bj',  # 北京证券交易所
                    }
                    
                    for suffix, prefix in exchange_map.items():
                        if code.endswith(suffix):
                            return f"{prefix}{code.replace(suffix, '')}"
                    
                    raise ValueError(f"未知的股票代码格式：{code}")
                # 代码转换
                symbol = convert_code(row['ts_code'])
                
                # 构造配置项
                config[row['name']] = {
                    "function": "stock_zh_a_daily",
                    "params": {
                        "symbol": symbol,
                        "start_date": list_date,
                        "end_date": datetime.today().strftime('%Y%m%d'),
                        "adjust": "hfq"
                    }
                }
            except Exception as e:
                print(f"处理股票 {row.get('name', '未知')} 时出错: {str(e)}")
                continue
        
        with yaml_path.open('w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            f.write(f"\n# 最后更新: {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
    except Exception as e:
        print(f"生成配置文件失败: {str(e)}")
        raise

def load_config(yaml_path: Union[str, Path] = DEFAULT_YAML_PATH) -> Dict:
    """加载YAML配置"""
    yaml_path = Path(yaml_path)
    try:
        with yaml_path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"加载配置文件失败: {str(e)}")
        raise

def fetch_stock_data(
    config: Dict,
    target_companies: Optional[List[str]] = None,
    max_workers: int = 4,
    batch_size: int = 20
) -> None:
    """优化的数据获取函数（批次处理版本）"""
    
    manifest_data = {}
    existing_manifest = load_manifest(MANIFEST_PATH)
    print('开始获取数据...')
    def process_batch(batch: List[str]) -> List[str]:
        """处理一个批次的公司数据"""
        updated_companies = []
        connection = None
        try:
            # 创建数据库连接
            connection = pymysql.connect(**db_config)
            cursor = connection.cursor()
            
            # 准备批量数据
            all_data = []
            for company in batch:
                # 重试逻辑
                retry_count = 0
                success = False
                while retry_count < 3 and not success:
                    try:
                        # 获取数据（原_fetch_data的核心逻辑）
                        if company not in config:
                            continue

                        # 日期处理逻辑
                        last_updated_str = existing_manifest.get(company, "")
                        list_date = config[company]["params"]["start_date"]
                        start_date = list_date
                        if last_updated_str:
                            last_date = datetime.strptime(last_updated_str, "%Y-%m-%d")
                            start_date = (last_date + timedelta(days=1)).strftime("%Y%m%d")
                        
                        today = datetime.today().strftime("%Y%m%d")
                        if start_date > today:
                            continue

                        # 获取数据
                        params = config[company]["params"].copy()
                        params.update({"start_date": start_date, "end_date": today})
                        stock_func = getattr(ak, config[company]["function"])
                        new_data = stock_func(**params)
                        
                        # 添加必要字段
                        new_data.insert(1, 'code', params["symbol"])
                        new_data.insert(2, 'symbol', company.strip())
                        
                        # 数据类型优化
                        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                                       'amount', 'outstanding_share', 'turnover']
                        for col in numeric_cols:
                            if col in new_data.columns:
                                new_data[col] = pd.to_numeric(new_data[col], errors='coerce', downcast='float')
                        
                        all_data.append(new_data)
                        updated_companies.append(company)
                        success = True  # 标记为成功
                    except Exception as e:
                        retry_count += 1
                        print(f"处理 {company} 失败（第 {retry_count} 次重试）: {str(e)}")
                        if retry_count < 3:
                            time.sleep(1)  # 等待1秒后重试
                            continue
                        else:
                            print(f"处理 {company} 失败，已重试3次，放弃处理。")
                            break
            # 合并数据并批量插入
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                
                # 数据预处理
                combined_df['date'] = pd.to_datetime(combined_df['date']).dt.date
                
                # 生成插入数据
                data_tuples = [tuple(x) for x in combined_df.to_records(index=False)]
                
                # 批量插入
                sql = """INSERT INTO stock_history 
                        (date, code, symbol, open, high, low, close, volume, 
                         amount, outstanding_share, turnover)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        open=VALUES(open), high=VALUES(high), low=VALUES(low),
                        close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount),
                        outstanding_share=VALUES(outstanding_share), turnover=VALUES(turnover)"""
                
                cursor.executemany(sql, data_tuples)
                connection.commit()
                print(f"成功插入批次数据：{len(data_tuples)} 条")

        except Exception as e:
            if connection:
                connection.rollback()
            print(f"批次处理失败: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
            # 显式释放内存
            del all_data
            gc.collect()
            
        return updated_companies

    # 分批次并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建批次任务
        batches = [target_companies[i:i+batch_size] 
                  for i in range(0, len(target_companies), batch_size)]
        
        futures = {executor.submit(process_batch, batch): batch 
                  for batch in batches}
        
        for future in as_completed(futures):
            # batch_companies = futures[future]
            try:
                updated = future.result()
                for company in updated:
                    manifest_data[company] = datetime.now().strftime("%Y-%m-%d")
            except Exception as e:
                print(f"批次处理异常: {str(e)}")

    # 更新清单文件
    try:
        updated_manifest = {**existing_manifest, **manifest_data}
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(updated_manifest, f,allow_unicode=True, sort_keys=False)
    except Exception as e:
        print(f"清单更新失败: {str(e)}")




def load_manifest(manifest_path: Union[str, Path]) -> Dict[str, str]:
    """加载YAML文件并返回公司名与时间的字典"""
    manifest_path = Path(manifest_path)
    try:
        if not manifest_path.exists():
            return {}
        with manifest_path.open('r', encoding='utf-8') as f:
            manifest_data = yaml.safe_load(f) or {}
        return manifest_data if isinstance(manifest_data, dict) else {}
    except yaml.YAMLError as e:
        print(f"YAML解析失败: {str(e)}")
        return {}
    except Exception as e:
        print(f"加载清单文件失败: {str(e)}")
        return {}




def deduplicate_companies(
    target_companies: List[str],
    manifest_path: Union[str, Path],
    interval_days: int = 30
) -> List[str]:
    """返回需要更新的公司列表（不存在于manifest或时间超过指定间隔）"""
    existing = load_manifest(manifest_path)
    need_update = []
    
    for company in target_companies:
        last_date_str = existing.get(company, "")
        if not last_date_str:
            need_update.append(company)
            continue
            
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            time_diff = datetime.now() - last_date
            if time_diff.days > interval_days:
                need_update.append(company)
        except ValueError:
            print(f"公司 {company} 的时间格式错误: {last_date_str}，需要强制更新")
            need_update.append(company)
    
    print(f"需要更新的公司数量: {len(need_update)}")
    return need_update

def main_workflow(
    target_companies: Optional[List[str]] = None,
    refresh_fundamental_data: bool = False,
    regenerate_config: bool = False,
    max_workers: int = 2,  # 降低默认并发数
    update_interval: int = 1,
    batch_size: int = 20
) -> None:

    try:
        if refresh_fundamental_data:
            get_stock_info()
            generate_yaml_config()
        elif regenerate_config:
            generate_yaml_config()
        
        config = load_config()
        
        if target_companies == ['all']:
            target_companies = list(config.keys())
        
        target_companies = deduplicate_companies(
            target_companies or [],
            MANIFEST_PATH,
            update_interval
        )
        
        fetch_stock_data(
            config=config,
            target_companies=target_companies,
            max_workers=max_workers,
            batch_size=batch_size
        )
    except Exception as e:
        print(f"流程异常: {str(e)}")
        raise

if __name__ == "__main__":
    DEFAULT_QUANT_DIR.mkdir(parents=True, exist_ok=True)
    
    main_workflow(
        target_companies=['all'],
        refresh_fundamental_data=False,
        regenerate_config=False,
        max_workers=4,
        update_interval=30,
        batch_size=10
    )
