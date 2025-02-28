eason-s_quant_platform


项目简介
这是一个为我及我的团队打造的量化平台，旨在通过整合多个数据源，高效地获取和处理股票数据，为量化分析和投资决策提供支持。截至2025年2月28日，仓库将包含两个主要步骤：`step_1`和`step_2`。其中，`step_1`主要基于`tushare`和`akshare`两个第三方数据源，实现股票信息的获取和数据处理。


功能概述

• 获取股票基本信息：通过`tushare`获取股票的基本信息（如股票代码、名称、上市日期等）并保存为 CSV 文件。

• 生成 YAML 配置文件：根据股票信息生成 YAML 配置文件，用于后续动态获取股票数据。

• 动态获取股票数据：基于 YAML 配置文件，使用`akshare`动态获取指定股票的历史数据。

• 保存数据：将获取的股票数据保存为 CSV 文件，方便后续分析。

• 灵活配置：支持自定义目标公司列表、数据存储路径等参数，便于用户根据需求调整。


使用方法


安装依赖
在使用本平台之前，请确保已安装以下依赖库：

```bash
pip install pandas tushare akshare pyyaml
```



获取股票基本信息
运行以下代码获取股票基本信息并保存到指定路径：

```python
from eason_quant_platform import get_stock_info

# 指定输出路径
output_path = "path/to/your/stock_company_info.csv"
get_stock_info(output_path)
```



生成 YAML 配置文件
根据股票信息生成 YAML 配置文件：

```python
from eason_quant_platform import generate_yaml_config

csv_path = "path/to/your/stock_company_info.csv"  # 股票 CSV信息 文件路径
yaml_path = "path/to/your/stock_config.yaml"  # 输出 YAML 配置文件路径
generate_yaml_config(csv_path, yaml_path)
```



动态获取股票数据
加载 YAML 配置文件并获取指定公司的股票数据：

```python
from eason_quant_platform import fetch_stock

# 指定目标公司列表
target_companies = ['中国联通', '中国移动', '中国电信']
# 指定 YAML 配置文件路径
yaml_path = "path/to/your/stock_config.yaml"
# 指定数据保存路径
save_path = "path/to/your/stock_data"

fetch_stock(target_companies=target_companies, yaml_path=yaml_path, save_path=save_path)
```



批量处理
使用`fetch_stock`函数可以一键完成从获取股票信息到保存数据的全流程：

```python
fetch_stock(
    target_companies=['平安银行', '招商银行', '万科A', '中国平安', '中国人寿', '中国石油', '中国联通', '中国移动', '中国电信'],
    csv_path="path/to/your/stock_company_info.csv",
    yaml_path="path/to/your/stock_config.yaml",
    save_path="path/to/your/stock_data",
    fetch_data=True,  # 是否重新获取股票信息
    regeneate_config=True  # 是否重新生成 YAML 配置文件
)
```



注意事项

• 数据源限制：

• `tushare`需要注册并获取 Token，具体操作请参考[tushare 官方文档]()。

• `akshare`的数据获取可能受到网络限制，请确保网络连接正常。

• 安全性：

• 在使用`eval`动态执行函数时，请确保 YAML 配置文件来源可信，避免潜在的安全风险。

• 路径配置：

• 请根据实际情况调整文件路径，确保路径有效且具有读写权限。

• 性能优化：

• 如果需要处理大量股票数据，建议分批处理以避免内存占用过高。

• 版本兼容性：

• 本项目基于 Python 3.8+开发，建议使用 Python 3.8 或更高版本运行。


未来计划

• step_2：进一步扩展功能，支持更多数据源和更复杂的数据处理逻辑。

• 优化性能：引入多线程或多进程处理，提升数据获取和处理效率。

• 增加可视化功能：支持数据可视化，方便用户快速分析和决策。


贡献与反馈
欢迎任何对本项目的贡献和反馈！如果你有任何问题或建议，请随时通过[GitHub Issues]()提出。
