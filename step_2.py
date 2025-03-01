import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import date
from pathlib import Path

DEFAULT_QUANT_DIR = Path.home() / "Desktop" / "quant"
FOLDER_PATH = DEFAULT_QUANT_DIR / "stock_data"
tab_0, tab_1 ,tab_2= st.tabs(["可视化","回测","数据池"])
def generate_candle_chart():
    col_a, col_b = st.columns(2)
    with tab_0:
        with col_a:
            with st.sidebar:
                if not st.session_state.data_pool:
                    st.warning("数据池为空，请先将数据加入数据池。")
                else:
                    with col5:
                        selected_dataset = st.selectbox(
                            "选择要可视化的数据集",
                            options=list(st.session_state.data_pool.keys()),
                            index=0,
                            key="selected_dataset_selectbox"
                        )
                        data = st.session_state.data_pool[selected_dataset]
                        timeframe = st.selectbox("时间粒度", ["day", "week", "month", "half_year"], key="timeframe_selectbox")
                    dataset_name = selected_dataset
                timeframe_mapping = {
                    'day': 'D',
                    'week': 'W',
                    'month': 'M',
                    'half_year': '6M'
                }
                resample_rule = timeframe_mapping.get(timeframe.lower(), timeframe)
                
            fig = go.Figure()
            
            # 转换日期并设置索引
            data = data.copy()
            data['date'] = pd.to_datetime(data['date'])
            data.sort_values('date', inplace=True)
            mask = (data['date'] >= pd.to_datetime(start_date)) & (data['date'] <= pd.to_datetime(end_date))
            data = data.loc[mask]

            try:
                with st.spinner('正在重采样数据...'):
                    data.set_index('date', inplace=True)
                    resampled = data.resample(resample_rule).agg({
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last'
                    }).dropna()
                    resampled.reset_index(inplace=True)
            except KeyError as e:
                st.warning(f"数据集缺少列 {e}，已跳过")
            # 日期范围筛选（使用重采样后的日期）
                # 添加K线图轨迹
            fig.add_trace(
                go.Candlestick(
                    x=resampled['date'],
                    open=resampled['open'],
                    high=resampled['high'],
                    low=resampled['low'],
                    close=resampled['close'],
                    name=f"{dataset_name} ({timeframe})",
                    visible=True,
                    opacity=0.7,
                    hoverinfo='text',
                    hovertext=f"{dataset_name}<br>日期: %{{x|%Y-%m-%d}}<br>"
                                f"开盘: %{{open:.2f}}<br>最高: %{{high:.2f}}<br>"
                                f"最低: %{{low:.2f}}<br>收盘: %{{close:.2f}}"
                )
            )
            # 优化布局配置
            fig.update_layout(
                title=f'多数据集K线对比 ({timeframe})',
                yaxis_title='价格',
                xaxis=dict(
                    tickmode='auto',
                    nticks=10 ,
                    tickformat='%Y-%m-%d',
                    rangeslider=dict(visible=False),
                    type='date'  ,
                    title='日期'
                    
                ),
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                template='plotly_dark'
            )
            st.plotly_chart(fig)

    with col_b:
        st.markdown("## 回测")
def generate_dynamic_chart():
    with st.sidebar:
        if not st.session_state.data_pool:
            st.warning("数据池为空，请先将数据加入数据池。")
        else:
            selected_datasets = st.multiselect(
            "选择要对比的多个数据集",
            options=list(st.session_state.data_pool.keys()),
            default=[list(st.session_state.data_pool.keys())[0]]
        )
            # 在 Streamlit 界面中修改列选择逻辑
            selected_columns = st.multiselect(
                "选择要可视化的列",
                options=['open', 'high', 'low', 'close', 'volume', 'amount','outstanding_share','turnover'],
                default=['close']  # 默认选中 close 列
            )

        # 在 Streamlit 界面部分替换原调用代码
        if not selected_datasets:  # 检查空列表
            st.warning("请选择数据集。")
        else:
            # 获取对应的数据列表
            data_list = [st.session_state.data_pool[key] for key in selected_datasets]
            normalize = st.checkbox("标准化显示", True, key="normalize_checkbox")
            smooth = st.checkbox("平滑处理", True, key="smooth_checkbox")
            window_size = st.slider("平滑窗口大小", 1, 100, 5, key="window_size_slider")
        if selected_columns is None:
            selected_columns = ['close']  # 默认选择 close 列
        selected_columns = list({*selected_columns, 'date'})  # 确保包含 date 列
        fig = go.Figure()

    # 遍历每个数据集
    for idx, (data, dataset_name) in enumerate(zip(data_list, selected_datasets)):
        # 日期筛选
        data = data[
            (pd.to_datetime(data['date']) >= pd.to_datetime(start_date)) &
            (pd.to_datetime(data['date']) <= pd.to_datetime(end_date))
        ].copy()
        
        # 处理选中的列
        valid_columns = [col for col in selected_columns if col in data.columns]
        if not valid_columns:
            st.warning(f"数据集 {dataset_name} 无有效列，已跳过")
            continue  # 跳过无有效列的数据
        # 数据预处理
        for col in valid_columns:
            # 平滑处理
            if smooth and np.issubdtype(data[col].dtype, np.number):
                data[col] = data[col].rolling(window=window_size, min_periods=1).mean().bfill()
                
            # 标准化处理
            if normalize and np.issubdtype(data[col].dtype, np.number):
                base_value = data[col].iloc[0] if data[col].iloc[0] != 0 else 1
                data[col] = data[col] / base_value * 100
        # 动态添加轨迹
        for col in valid_columns:
            if col == 'date':
                continue
            fig.add_trace(
                go.Scatter(
                    x=data['date'] if 'date' in data.columns else data.index,
                    y=data[col],
                    name=f"{dataset_name} - {col}",  # 组合名称
                    mode='lines',
                    line_shape='linear',
                    visible=True if idx == 0 else 'legendonly',  # 默认只显示第一个
                    opacity=0.7,
                    hovertemplate=f"{dataset_name}<br>日期: %{{x}}<br>{col}: %{{y}}"
                )
            )

    # 统一图表样式
    fig.update_layout(
        title='多数据集对比',
        yaxis_title='标准化数值 (%)' if normalize else '原始数值',
        xaxis_title='日期' if 'date' in data.columns else '索引',
        hovermode='x unified',
        legend=dict(title='数据集/列', orientation='h', yanchor='bottom', y=1.02)
    )
    st.plotly_chart(fig)

@st.cache_data(show_spinner="正在加载文件...")
def load_single_file(file_path: Path):
    """ 缓存单个文件的加载过程 """
    try:# 在加载函数中添加调试信息
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path, encoding='utf-8-sig')  # 处理BOM头
        elif file_path.suffix == '.xlsx':
            return pd.read_excel(file_path)
    except Exception as e:
        
        return None

# 监控文件夹变化（通过hash函数实现）
@st.cache_data(hash_funcs={Path: lambda p: p.stat().st_mtime})
def get_folder_files(path: Path):
    return list(path.glob("*.csv"))

def clear_data_pool():
    st.session_state.data_pool = {}
def clear_process_pool():
    st.session_state.process_pool = {}






main_container = st.container()


if not FOLDER_PATH.exists():
    st.error(f"文件夹不存在：{FOLDER_PATH}")
if "data_pool" not in st.session_state:
    st.session_state.data_pool = {}
if "process_pool" not in st.session_state:
    st.session_state.process_pool = {}





with st.sidebar:

    # 文件选择器（保持动态更新）
    all_files = [f for f in FOLDER_PATH.iterdir() if f.is_file()]
    selected_files = st.multiselect("选择文件", all_files,format_func=lambda x: x.name)

    col3, col4 = st.columns(2)
    with col3:
        if st.button("添加到数据池"):
            for file in selected_files:
                # 调用缓存加载函数
                data = load_single_file(file)
            if data is not None:
                st.session_state.data_pool[file.name] = data
    with col4:
        if st.button("强制刷新缓存"):
            load_single_file.clear()  
            st.cache_data.clear()

    col1, col2 = st.columns(2)

    with col1:
        st.header("数据池")
        if st.button("清空数据池"):
            st.session_state.data_pool = {}
        if st.session_state.data_pool:
            for key, value in st.session_state.data_pool.items():
                st.write(f"{key.replace('.csv', '')}")
            st.metric("数据池内存", f"{sum(df.memory_usage().sum() for df in st.session_state.data_pool.values())/1e6:.1f}MB")
        else:
            st.info("数据池为空")


    with col2:
        st.header("进程池")
        if st.button("清空进程池"):
            st.session_state.process_pool = {}
        if st.session_state.process_pool:
            for key, value in st.session_state.process_pool.items():
                st.write(f"任务名：{key}")
                st.write(value)  # 显示任务的状态
                st.metric("数据池内存", f"{sum(df.memory_usage().sum() for df in st.session_state.process_pool.values())/1e6:.1f}MB")
        else:
            st.info("进程池为空")

    date_container = st.container()
    date_range = st.slider(
    "选择日期范围",
    min_value=date(2000, 1, 1),
    max_value=date(2025, 1, 1),
    value=(date(2015, 1, 1), date(2024, 12, 31)),
    format="YYYYMMDD"
)
    with date_container:
        begin_date_col, end_date_col = st.columns(2)
        with begin_date_col:
            start_date = st.date_input(
                "微调开始日期",
                value=date_range[0],
                min_value=date(2000, 1, 1),
                max_value=date_range[1]
            )
        with end_date_col:
            end_date = st.date_input(
            "微调结束日期",
            value=date_range[1],
            min_value=start_date,
            max_value=date(2025, 1, 1)
            )
    col5, col6 = st.columns(2)
    with col5:
        st.selectbox("选择可视化类型", ["K线图", "动态图"], key="chart_type_selectbox")
    st.write(f"查看文件夹：{FOLDER_PATH}")

    if st.session_state.chart_type_selectbox == "K线图":
        with main_container:
            generate_candle_chart()
    elif st.session_state.chart_type_selectbox == "动态图":
        with main_container:
            generate_dynamic_chart()
