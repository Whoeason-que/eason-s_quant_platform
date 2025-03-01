# Eason Quant Platform

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

面向量化研究的全流程解决方案，整合多数据源采集、自动化配置管理、高性能数据处理与交互式可视化分析。

**最新进展** (2024.6) ➜ 新增Streamlit可视化仪表盘，支持多维度数据对比分析

## 功能架构

```mermaid
graph TD
    A[数据采集层] --> B[配置管理层]
    B --> C[核心处理层]
    C --> D[应用接口层]
    D --> E[可视化展示层]
    
    A -->|Tushare| A1[基础信息采集]
    A -->|AKShare| A2[历史行情获取]
    
    B --> B1[YAML配置生成]
    B --> B2[动态函数映射]
    
    C --> C1[多线程处理]
    C --> C2[异常处理]
    
    D --> D1[数据持久化]
    D --> D2[API服务]
    
    E --> E1[K线对比]
    E --> E2[动态图表]
    E --> E3[回测框架]
  ```
## 核心特性

### 数据采集与处理
- 多源集成：支持Tushare/AKShare等主流数据源
- 智能配置：自动生成可维护的YAML配置文件
- 并发处理：基于ThreadPoolExecutor实现多线程数据获取
- 数据规范：
  ```python
  {
    "symbol": "sh600000",      # 标准证券代码
    "start_date": "19991110",  # 上市日期
    "adjust": "hfq",           # 复权类型
    # 数据字段规范...
  }
  ```

### 可视化分析 (Streamlit)
- **多视图对比**：支持K线图与动态趋势图双模式
- 交互功能：
  - 时间粒度选择（日/周/月/半年）
  - 多数据集叠加分析
  - 数据标准化与平滑处理
- 数据池管理：
  ```bash
  ├── 内存管理：自动计算数据集内存占用
  ├── 动态加载：支持CSV/Excel格式
  └── 缓存机制：基于文件修改时间的智能刷新
  ```

## 快速开始

### 环境配置
```bash
# 基础依赖
pip install pandas tushare akshare pyyaml

# 可视化组件
pip install streamlit plotly numpy
```

### 数据管道使用
```python
from step_1 import main_workflow

# 示例：全流程获取金融数据
main_workflow(
    target_companies=['贵州茅台', '宁德时代'],
    refresh_data=True,
    regenerate_config=True,
    max_workers=12
)
```

### 启动可视化仪表盘
```bash
streamlit run visualization_app.py --server.port 8501
```
![可视化界面示例](https://via.placeholder.com/800x400?text=K线对比+动态趋势分析)

## 高级功能

### 配置自定义
通过修改`stock_config.yaml`实现：
```yaml
# 数据结构示例
中国平安:
  function: stock_zh_a_daily    # AKShare函数名
  params:
    symbol: sh601318           # 标准代码格式
    start_date: "20070301"     # 数据起始日期
    adjust: hfq                # 后复权模式
```

### 性能调优参数
| 参数            | 类型   | 默认值 | 说明                     |
|-----------------|--------|--------|--------------------------|
| `max_workers`   | int    | 8      | 最大并发线程数           |
| `fetch_data`    | bool   | False  | 强制刷新基础数据         |
| `smooth_window` | int    | 5      | 数据平滑窗口大小         |

## 开发指南

### 扩展数据源
1. 在`stock_config.yaml`中添加新配置项
2. 实现对应的数据解析函数
3. 更新`convert_code()`中的交易所映射表

### 调试模式
```python
# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    handlers=[logging.FileHandler('debug.log'), logging.StreamHandler()]
)
```

## 最佳实践

1. **增量更新**：通过设置`refresh_data=False`复用已有数据
2. **内存优化**：使用`DEFAULT_QUANT_DIR`集中管理数据路径
3. **安全建议**：将Token等敏感信息移出版本控制
   ```python
   # 从环境变量读取凭证
   import os
   ts.set_token(os.getenv('TUSHARE_TOKEN'))
   ```

## 路线图

| 版本    | 里程碑                          | 状态    |
|---------|---------------------------------|---------|
| v1.0    | 基础数据管道搭建                | ✓ 已完成|
| v1.5    | Streamlit可视化模块             | ✓ 已完成|
| v2.0    | 回测框架与策略库                | 开发中  |
| v2.5    | 分布式数据抓取                  | 规划中  |

## 贡献与支持

欢迎通过以下方式参与项目：
- 提交Pull Request完善文档
- 在Issues报告数据源异常
- 贡献量化策略案例

**特别提示**：使用eval动态加载函数时，请严格验证YAML文件来源，建议在生产环境中禁用此特性。

[查看完整贡献指南](CONTRIBUTING.md) | [许可证信息](LICENSE)
```
