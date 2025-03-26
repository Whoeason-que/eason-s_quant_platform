import os
import datetime
import pandas as pd
import streamlit as st
import backtrader as bt
import quantstats as qs
import plotly.graph_objects
import threading
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
from pathlib import Path
from 策略 import select_strategy
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
st.set_page_config(layout="wide")
DEFAULT_QUANT_DIR = Path.home() / "Desktop" / "quant"
FOLDER_PATH = DEFAULT_QUANT_DIR / "stock_data"
report_dir = DEFAULT_QUANT_DIR / '回测报告'

class DataFeed:
    def __init__(self):
        self.folder_path = FOLDER_PATH
        self.data_files = [f for f in os.listdir(self.folder_path) if f.endswith('.csv')]
        self.selected_files = st.sidebar.multiselect("选择股票数据文件", self.data_files)
        if self.selected_files:
            self.filter_data = st.sidebar.checkbox("滤波数据")
            if self.filter_data:
                self.start_date = st.sidebar.date_input("开始日期", datetime.date(2010, 1, 1))
                self.end_date = st.sidebar.date_input("结束日期", datetime.date.today())

    def process_data(self):
        data_list = []
        for file in self.selected_files:
            data_path = os.path.join(self.folder_path, file)
            try:
                data = pd.read_csv(data_path)
            except Exception as e:
                st.error(f"无法读取文件 {file}: {str(e)}")
                continue

            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_columns):
                st.error(f"文件 {file} 缺少必要的列: {', '.join(required_columns)}")
                return None

            try:
                data['date'] = pd.to_datetime(data['date'])
                data = data.sort_values('date')
            except Exception as e:
                st.error(f"文件 {file} 日期格式错误: {str(e)}")
                continue

            if self.filter_data:
                mask = (data['date'] >= pd.to_datetime(self.start_date)) & (data['date'] <= pd.to_datetime(self.end_date))
                data = data[mask].copy()
                if data.empty:
                    st.warning(f"文件 {file} 在指定日期范围内没有数据")
                    continue

            data_sorted = data.set_index('date')
            data_list.append(data_sorted)

        return sorted(data_list, key=lambda x: x.index[0]) if data_list else None

def show_history_reports():
    if report_dir.exists():
        # 获取目录下的所有HTML文件
        history_files = [f for f in os.listdir(report_dir) if f.endswith('.html')]
        
        if history_files:
            # 创建一个下拉选择框
            selected_file = st.selectbox("选择要展示的回测报告", history_files)
            
            # 创建一个按钮
            if st.button("打开报告"):
                # 构建本地HTML文件的路径
                html_path = report_dir / selected_file
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                st.components.v1.html(html_content, width=2000, height=1000, scrolling=True)
        else:
            st.write("没有找到历史回测报告文件。")
    else:
        st.write("历史回测报告目录不存在。")
def show_lines_chart(data_list):
    fig=plotly.graph_objects.Figure()
    if data_list:
        for data in data_list:
            fig.add_trace(plotly.graph_objects.Scatter(x=data.index, y=data['close']))
        st.plotly_chart(fig, use_container_width=True)
def quantstats_report(result):
    qs.extend_pandas()
    report_dir.mkdir(exist_ok=True)
    params = result.params._getkwargs()  # 获取所有参数字典
    try:
        returns, _, _, _ = result.analyzers.getbyname('pyfolio').get_pf_items()
    except Exception as e:
        st.error(f"获取回测结果失败: {str(e)}")
        return
    
    # 动态生成参数描述
    param_desc = "_".join([f"{k}={v}" for k, v in params.items()])
    timestamp = datetime.datetime.now().strftime('%m-%d-%H-%M-%S')
    report_name = f"{timestamp}_{param_desc[:150]}.html"  # 限制文件名长度
    
    try:
        qs.reports.html(returns, output=str(report_dir/report_name))
        st.success(f"报告已生成: {report_name}")
    except Exception as e:
        st.error(f"生成报告失败: {str(e)}")
def main():
    st.title("多资产组合优化回测系统")
    
    # 策略选择
    st.sidebar.header("策略配置")
    
    data_loader = DataFeed()
    data_list = data_loader.process_data()
    show_lines_chart(data_list)
    if not data_list:
        st.warning("请选择至少一个数据文件")
        show_history_reports()
        return
    
    # 动态参数配置
    st.sidebar.header("回测参数")
    
    cerebro = bt.Cerebro()
    cerebro.addanalyzer(bt.analyzers.PyFolio, _name='pyfolio')
    for data in data_list:
        cerebro.adddata(bt.feeds.PandasData(dataname=data.copy()))
    
    cerebro.broker.setcash(100000)
    cerebro.broker.setcommission(0.005)
    cerebro.broker.set_slippage_perc(0.005)
    select_strategy(cerebro)


    if st.sidebar.button("开始回测"):
        results = cerebro.run()
        st.success("回测完成")
        # cerebro.plot(style='candlestick')
        # 生成QuantStats报告
        # if isinstance(results, list) and len(results) > 0 and isinstance(results[0], list):
        #     for result in results:
        #         quantstats_report(result[0])
        # else:
        #     quantstats_report(results[0])
    show_history_reports()

if __name__ == '__main__':
    main()
'''
streamlit run 回测.py --server.runOnSave true --server.enableCORS true
'''
