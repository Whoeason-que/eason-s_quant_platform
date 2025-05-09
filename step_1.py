import pandas as pd
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import tushare as ts
import akshare as ak
from pathlib import Path
from typing import Optional, List, Dict,Literal, Union
import logging
import signal
import sys
import time
import random

# 基础路径配置（跨平台兼容）
DEFAULT_QUANT_DIR = Path.home() / "Desktop" / "quant"
DEFAULT_CSV_PATH = DEFAULT_QUANT_DIR / "stock_company_info.csv"
DEFAULT_YAML_PATH = DEFAULT_QUANT_DIR / "stock_config.yaml"
DEFAULT_SAVE_PATH = DEFAULT_QUANT_DIR / "stock_data"

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(DEFAULT_QUANT_DIR / "stock_downloader.log"),
        logging.StreamHandler()
    ]
)

# 定义信号处理函数
def signal_handler(sig, frame):
    logging.info('程序中断，正在安全退出...')
    sys.exit(0)

def get_stock_info(output_path: Union[str, Path] = DEFAULT_CSV_PATH) -> None:
    """获取股票基本信息并保存到CSV"""
    output_path = Path(output_path)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        pro = ts.pro_api()# 初始化tushare pro接口,这里需要先在tushare注册账号
        df = pro.stock_basic(
            exchange='', 
            list_status='L', 
            fields='ts_code,symbol,name,list_date,industry'
        )
        df.to_csv(output_path, index=False)
        logging.info(f"股票基本信息已保存至 {output_path.resolve()}")
    except Exception as e:
        logging.error(f"获取股票信息失败: {str(e)}")
        raise

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

def generate_yaml_config(
    csv_path: Union[str, Path] = DEFAULT_CSV_PATH,
    yaml_path: Union[str, Path] = DEFAULT_YAML_PATH
) -> None:
    """生成YAML配置文件"""
    csv_path = Path(csv_path)
    yaml_path = Path(yaml_path)
    
    try:
        data = pd.read_csv(csv_path)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {}
        for _, row in data.iterrows():
            try:
                # 验证必要字段
                if not all(pd.notna(row[field]) for field in ['ts_code', 'name', 'list_date']):
                    continue
                    
                # 处理上市日期
                list_date = str(int(float(row['list_date']))) if pd.notna(row['list_date']) else ""
                if len(list_date) != 8 or not list_date.isdigit():
                    continue
                
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
                logging.warning(f"处理股票 {row.get('name', '未知')} 时出错: {str(e)}")
                continue
        
        with yaml_path.open('w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, sort_keys=False)
            f.write(f"\n# 最后更新: {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        logging.info(f"配置文件已生成: {yaml_path.resolve()}")
    except Exception as e:
        logging.error(f"生成配置文件失败: {str(e)}")
        raise

def load_config(yaml_path: Union[str, Path] = DEFAULT_YAML_PATH) -> Dict:
    """加载YAML配置"""
    yaml_path = Path(yaml_path)
    try:
        with yaml_path.open('r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {str(e)}")
        raise

def fetch_stock_data(
    config: Dict,
    delay_min: float = 1,
    delay_max: float = 3,
    target_companies: Optional[List[str]] = None,
    max_workers: int = 8,
    output_dir: Union[str, Path] = DEFAULT_SAVE_PATH
) -> Dict[str, pd.DataFrame]:
    """多线程获取股票数据并立即保存到CSV"""
    results = {}
    target_companies = target_companies or list(config.keys())
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    def _fetch_data(company: str, delay_min: float = 1, delay_max: float = 3) -> Optional[pd.DataFrame]:
        try:
            # 添加随机延迟
            delay = random.uniform(delay_min, delay_max)  # 1到3秒的随机延迟
            logging.info(f"等待 {delay:.2f} 秒以防止频繁访问...")
            time.sleep(delay)
            
            if company not in config:
                logging.warning(f"跳过未配置公司: {company}")
                return None
            
            func_name = config[company]["function"]
            params = config[company]["params"]
            
            # 动态获取akshare函数
            if not hasattr(ak, func_name):
                logging.error(f"无效函数名: {func_name}")
                return None
                
            stock_func = getattr(ak, func_name)
            data = stock_func(**params)
            
            if not isinstance(data, pd.DataFrame) or data.empty:
                logging.warning(f"空数据: {company}")
                return None
                
            # 保存数据到CSV
            safe_name = "".join(c if c.isalnum() else "_" for c in company)
            file_path = output_dir / f"{safe_name}.csv"
            data.to_csv(file_path, index=False)
            logging.info(f"已保存 {company} 数据到 {file_path}")
            
            return data
        except Exception as e:
            logging.error(f"获取 {company} 数据失败: {str(e)}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_fetch_data, company): company
            for company in target_companies
        }
        
        for future in as_completed(future_map):
            company = future_map[future]
            try:
                data = future.result()
                if data is not None:
                    results[company] = data
                    logging.info(f"成功获取 {company} 数据 ({len(data)} 条)")
            except Exception as e:
                logging.error(f"处理 {company} 时发生异常: {str(e)}")

    return results

def main_workflow(
    target_companies: Optional[List[str]] = None,
    refresh_fundamental_data: bool = False,
    regenerate_config: bool = False,
    max_workers: int = 8,
    stock_sector: Optional[List[Literal['hs300', 'cyb50', 'industry:银行', 'industry:科技']]] = None
) -> None:
    """主工作流程
    stock_sector: 支持多种筛选模式 
        hs300 - 沪深300成分股
        cyb50 - 创业板50
        industry:XXX - 按行业筛选
    """
    try:
        # 注册信号处理函数
        signal.signal(signal.SIGINT, signal_handler)
        
        # 初始化默认参数
        stock_sector = stock_sector or []
        target_companies = target_companies or ["中国联通", "中国移动", "中国电信"]
        
        # 板块筛选逻辑
        if stock_sector:
            sector_data = pd.read_csv(DEFAULT_CSV_PATH)
            selected_codes = []
            
        # 更新股票列表
        if refresh_fundamental_data:
            get_stock_info()
            
        # 生成配置文件
        if regenerate_config or refresh_fundamental_data:
            generate_yaml_config()
            
        # 加载配置
        config = load_config()
        
        # 获取数据
        stock_data = fetch_stock_data(
            config=config,
            target_companies=target_companies,
            max_workers=max_workers
        )
    except Exception as e:
        logging.error(f"主流程执行失败: {str(e)}")
        raise

if __name__ == "__main__":
    # 注册信号处理函数
    signal.signal(signal.SIGINT, signal_handler)
    
    # 初始化目录
    DEFAULT_QUANT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 示例调用
    main_workflow(
        target_companies=['汉威科技'],
        refresh_fundamental_data=False,
        regenerate_config=False,
        max_workers=12,
    )
