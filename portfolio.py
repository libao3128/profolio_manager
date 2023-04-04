from datetime import datetime
import pandas as pd
import numpy as np
from datetime import date
import yfinance as yf

from data import Record, Query, Price
import pandas_market_calendars as mcal

class Portfolio:
    def __init__(self, account_name) -> None:
        self.name = account_name

        self.cash = 0
        self.cal_stock_value = None
        self.start_date = None
        
        self.record = Record()

    def from_csv(self, file):
        self.record.from_csv(file)
    
    def save_history(self):
        self.history.to_excel(self.name+"_history.xlsx")

    def save_buy_sell_pair(self):
        self.buy_sell_pair['Total Gain/Loss	'] = self.buy_sell_pair['SalesProceeds'] - self.buy_sell_pair['Cost']
        self.buy_sell_pair.to_excel(self.name+"_Gain_Loss.xlsx")

    @property
    def cash_balance(self):
        daily_amount = self.record.daily_transaction_amount
        data = daily_amount.cumsum()
        
        nyse = mcal.get_calendar('NYSE')
        date_range = nyse.schedule(start_date=self.record.start_date, end_date=datetime.now().strftime('%Y-%m-%d')).index
        cash_balance = pd.DataFrame(data= data,index=date_range, columns=data.columns)
        cash_balance = cash_balance.fillna(method='ffill')
        cash_balance = cash_balance.applymap(lambda x: x if x>=0 else 0)
        
        return cash_balance['Amount']
    
    @ property
    def margin_balance(self):
        daily_amount = self.record.daily_transaction_amount
        data = daily_amount.cumsum()
        nyse = mcal.get_calendar('NYSE')
        date_range = nyse.schedule(start_date=self.record.start_date, end_date=datetime.now().strftime('%Y-%m-%d')).index
        margin_balance = pd.DataFrame(data= data,index=date_range, columns=data.columns)
        margin_balance = margin_balance.fillna(method='ffill')
        margin_balance = margin_balance.applymap(lambda x: -x if x<=0 else 0)
        
        return margin_balance['Amount']
    
    @ property
    def position(self):
        transactions = Query.TradeTransaction(self.record.record)
        transactions = transactions.set_index('TradeDate')
        nyse = mcal.get_calendar('NYSE')
        date_range = nyse.schedule(start_date=self.record.start_date, end_date=datetime.now().strftime('%Y-%m-%d')).index
        positions = pd.DataFrame(index=date_range)
        
        for date in positions.index:
            # 获取在这一天之前所有的交易
            trades = transactions.loc[:date]

           # print(trades)
            #print(trades.groupby('Symbol')['Quantity'].sum())
            amount = trades.groupby('Symbol')['Quantity'].sum()
           # 
            #p rint(amount)
            # 计算每个证券的持仓股数
            if len(amount)>0:
                positions.loc[date,amount.index] = amount
            
        positions = positions.fillna(method='ffill')
        positions = positions.fillna(value=0)
        return positions.copy()

    @ property
    def position_value(self):
        position = self.position
        position_value = pd.DataFrame(index=position.index, columns=position.columns)
        price_bank = Price()
        for ticker in position.columns:
            close_prices = price_bank.get_prices(ticker)
            #print(close_prices)
            position_value[ticker] = position[ticker]*close_prices['close']
        position_value['total'] = position_value.sum(axis=1)
        return position_value

    @property
    def account_value(self):
        return self.cash_balance+self.position_value['total']-self.margin_balance
    @property
    def principal_value(self):
        nyse = mcal.get_calendar('NYSE')
        date_range = nyse.schedule(start_date=self.record.start_date, end_date=datetime.now().strftime('%Y-%m-%d')).index

       
        value = self.record.deposit_transaction
        print('value',value)
        
        value.index = pd.DatetimeIndex(value['TradeDate'])
        value = value.reindex(date_range)
        #print(value)
        #value.reset_index(date_range)
        #value = value['Amount']
        value['Amount'] = value['Amount'].fillna(0)
        value['Amount'] = value['Amount'].cumsum(skipna=False)
        return value.copy()['Amount']
if __name__ == '__main__':
    portfolio = Portfolio('Firstrade')
    portfolio.from_csv('data\FT_CSV_87748402.csv')
    #print(profolio.cash_flow)
    #print(profolio.storage.groupby('Symbol').sum()['Remain_Quant'])
    #print(profolio.cash_balance)
    #print(profolio.margin_balance)
    #print(profolio.position)
    #print(profolio.position_value)
    print(portfolio.position_value)