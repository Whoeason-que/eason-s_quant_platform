import backtrader as bt
import streamlit as st
import pandas as pd
import datetime
class SMAStrategy(bt.Strategy):
    params = (
        ('maperiod', 20),  # SMA周期
    )

    def __init__(self):
        # 为每个数据源初始化SMA指标
        self.smas = {}
        for d in self.datas:
            self.smas[d] = bt.indicators.SimpleMovingAverage(d, period=self.params.maperiod)
    def prenext(self):
        self.next()
    def next(self):
        # 遍历所有数据源
        for d in self.datas:
            # 如果当前数据源没有持仓
            if not self.getposition(d).size:
                # 如果当前价格高于SMA，买入
                #如果有剩余资金
                if d.close[0] > self.smas[d][0]:
                    if self.broker.getcash() > d.close[0]:
                        self.buy(data=d)
            # 如果当前数据源有持仓
            else:
                # 如果当前价格低于SMA，卖出
                if d.close[0] < self.smas[d][0]:
                    self.sell(data=d)
class DualMAStrategy(bt.Strategy):
    params = (
        ('short_period', 10),  # 短期均线周期
        ('long_period', 30),   # 长期均线周期
    )

    def __init__(self):
        # 为每个数据源初始化短期和长期均线以及交叉信号
        self.short_smass = {}
        self.long_smass = {}
        self.crossovers = {}
        for d in self.datas:
            short_sma = bt.indicators.SimpleMovingAverage(d, period=self.params.short_period)
            long_sma = bt.indicators.SimpleMovingAverage(d, period=self.params.long_period)
            self.short_smass[d] = short_sma
            self.long_smass[d] = long_sma
            self.crossovers[d] = bt.indicators.CrossOver(short_sma, long_sma)
    def prenext(self):
        self.next()
    def next(self):
        # 遍历所有数据源
        for d in self.datas:
            # 如果当前数据源没有持仓
            if not self.getposition(d).size:
                # 如果短期均线上穿长期均线，买入
                if self.crossovers[d] > 0:
                    if self.broker.getcash() > d.close[0]:
                        self.buy(data=d)
            # 如果当前数据源有持仓
            else:
                # 如果短期均线下穿长期均线，卖出
                if self.crossovers[d] < 0:
                    self.sell(data=d)
class MACDStrategy(bt.Strategy):
    params = (
        ('short_period', 10),  # 短期均线周期
        ('long_period', 30),   # 长期均线周期
    )

    def __init__(self):
        # 为每个数据源初始化短期和长期均线以及交叉信号
        self.short_smass = {}
        self.long_smass = {}
        self.crossovers = {}
        for d in self.datas:
            short_sma = bt.indicators.SimpleMovingAverage(d, period=self.params.short_period)
            long_sma = bt.indicators.SimpleMovingAverage(d, period=self.params.long_period)
            self.short_smass[d] = short_sma
            self.long_smass[d] = long_sma
            self.crossovers[d] = bt.indicators.CrossOver(short_sma, long_sma)

    def next(self):
        # 遍历所有数据源
        for d in self.datas:
            # 如果当前数据源没有持仓
            if not self.getposition(d).size:
                # 如果短期均线上穿长期均线，买入
                if self.crossovers[d] > 0:
                    if self.broker.getcash() > d.close[0]:
                        self.buy(data=d)
            # 如果当前数据源有持仓
            else:
                # 如果短期均线下穿长期均线，卖出
                if self.crossovers[d] < 0:
                    self.sell(data=d)



Strategy =['SMA策略', '双均线策略', 'MACD策略', '自定义策略0']
def select_strategy(cerebro):
    strategy_name = st.sidebar.selectbox("选择策略", Strategy)
    optimization = st.sidebar.checkbox("启用参数优化")
    if strategy_name == 'SMA策略':
        if optimization:
            cerebro.optstrategy(SMAStrategy, maperiod=range(10, 30))
        else:    
            cerebro.addstrategy(SMAStrategy)
    elif strategy_name == '双均线策略':
        if optimization:
            cerebro.optstrategy(DualMAStrategy, short_period=range(5, 6), long_period=range(10, 12))
        else:    
            cerebro.addstrategy(DualMAStrategy)
    elif strategy_name == 'MACD策略':
        if optimization:
            cerebro.optstrategy(MACDStrategy, short_period=range(5, 10), long_period=range(10, 20))
        else:    
            cerebro.addstrategy(MACDStrategy)
    elif strategy_name == '自定义策略0':
        pass
    return
