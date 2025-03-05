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

# 基础路径配置（跨平台兼容）
DEFAULT_QUANT_DIR = Path.home() / "Desktop" / "quant"
DEFAULT_CSV_PATH = DEFAULT_QUANT_DIR / "stock_company_info.csv"
DEFAULT_YAML_PATH = DEFAULT_QUANT_DIR / "stock_config.yaml"
DEFAULT_SAVE_PATH = DEFAULT_QUANT_DIR / "stock_data"
MANIFEST_PATH = DEFAULT_SAVE_PATH / "manifest.yaml"  # 新增清单文件路径

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
                list_date = str(row['list_date']).strip().replace("-", "")
                if not list_date.isdigit() or len(list_date) != 8:
                    logging.warning(f"无效上市日期: {row['name']} - {row['list_date']}")
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
    target_companies: Optional[List[str]] = None,
    max_workers: int = 4,
    output_dir: Union[str, Path] = DEFAULT_SAVE_PATH
) -> None:
    """多线程获取股票数据并立即保存到CSV"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_data = {}

    # 修改_fetch_data函数中的参数处理
    def _fetch_data(company: str) -> Optional[pd.DataFrame]:
        try:
            if company not in config:
                logging.warning(f"跳过未配置公司: {company}")
                return None
            
            # 获取函数配置
            func_name = config[company]["function"]
            params = config[company]["params"].copy()  # 创建参数副本
            
            # 动态更新结束日期
            params["end_date"] = datetime.today().strftime('%Y%m%d')
            
            # 验证函数有效性
            if not hasattr(ak, func_name):
                logging.error(f"无效函数名: {func_name}")
                return None
                
            # 获取函数对象
            stock_func = getattr(ak, func_name)
            
            # 调用函数
            data = stock_func(**params)
            
            # 数据验证
            if not isinstance(data, pd.DataFrame) or data.empty:
                logging.warning(f"空数据: {company}")
                return None
                
            # 保存文件
            safe_name = "".join(c if c.isalnum() else "_" for c in company)
            file_path = output_dir / f"{safe_name}.csv"
            data.to_csv(file_path, index=False)
            logging.info(f"已保存 {company} 数据到 {file_path}")
            
            return company
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
                T = datetime.now().strftime("%Y-%m-%d")
                future.result()
                manifest_data[company] = T
                logging.info(f"成功获取 {company} 数据")
            except Exception as e:
                logging.error(f"处理 {company} 时发生异常: {str(e)}")
    
    try:
        # 读取现有清单
        existing_manifest = load_manifest(MANIFEST_PATH)
        # 合并新数据（自动覆盖旧记录）
        existing_manifest.update(manifest_data)
        
        # 写入更新后的清单
        with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
            yaml.dump(
                existing_manifest,
                f,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False
            )
        logging.info(f"清单文件已更新，共维护 {len(existing_manifest)} 条公司记录")
    except Exception as e:
        logging.error(f"更新清单文件失败: {str(e)}")
        raise

def main_workflow(
    target_companies: Optional[List[str]] = None,
    refresh_fundamental_data: bool = False,
    regenerate_config: bool = False,
    max_workers: int = 8,
    update_interval: int = 30  # 新增时间间隔参数
) -> None:

    try:
        # 注册信号处理函数
        signal.signal(signal.SIGINT, signal_handler)
        # 更新股票列表
        if refresh_fundamental_data:
            get_stock_info()
            
        # 生成配置文件
        if regenerate_config or refresh_fundamental_data:
            generate_yaml_config()
            
        # 加载配置
        config = load_config()
        
        if target_companies == ['all']:
            target_companies = list(config.keys())
            target_companies = deduplicate_companies(
                target_companies,
                MANIFEST_PATH,
                interval_days=update_interval
            )
        else:
            target_companies = deduplicate_companies(
                target_companies or [],
                MANIFEST_PATH,
                interval_days=update_interval
            )
        # 获取数据（删除原来的generate_manifest调用）
        fetch_stock_data(
        config=config,
        target_companies=target_companies,
        max_workers=max_workers
        )
    except Exception as e:
        logging.error(f"主流程执行失败: {str(e)}")
        raise
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
        logging.error(f"YAML解析失败: {str(e)}")
        return {}
    except Exception as e:
        logging.error(f"加载清单文件失败: {str(e)}")
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
            logging.warning(f"公司 {company} 的时间格式错误: {last_date_str}，需要强制更新")
            need_update.append(company)
    
    logging.info(f"需要更新的公司数量: {len(need_update)}")
    return need_update
if __name__ == "__main__":

    # 初始化目录
    DEFAULT_QUANT_DIR.mkdir(parents=True, exist_ok=True)
    
    main_workflow(
        target_companies=['唐人神'],
        refresh_fundamental_data=False,
        regenerate_config=False,
        max_workers=4,
        update_interval=0  # 可根据需要调整更新间隔
    )
