from datetime import datetime
import pandas as pd
import numpy as np
from datetime import date
import yfinance as yf

class Profolio:
    def __init__(self, account_name) -> None:
        self.name = account_name
        self.history = pd.DataFrame(
            columns=['Symbol', 'Quantity', 'Price', 'Action', 'TradeDate', 'Amount', 'RecordType'])
        self.buy_sell_pair = pd.DataFrame(
            columns=['Symbol','DateAcquired', 'DateSold', 'DaysHeld', 'SalesProceeds', 'Cost', 'Quantity', 'InIndex', 'OutIndex']
        )
        self.cash = 0
        self.cal_stock_value = None

    def from_csv(self, file):
        df = pd.read_csv(file)
        self.history = pd.concat([self.history, df[self.history.columns]])
        self.history['Symbol'] = self.history['Symbol'].str.strip()
        self.history = self.history.replace('FB', 'META')

        symbols = self.history['Symbol'].unique()
        
        for s in symbols:
            self.__build_buy_sell_pair(s)

    def __build_buy_sell_pair(self, symbol):
        Q = 0
        transaction = self.history[self.history['Symbol']==symbol]
        transaction = transaction[transaction['RecordType']=='Trade']
        transaction.loc[:,'Remain_Quant'] = transaction.loc[:,'Quantity']
        #print(transaction)
        transaction = transaction[transaction['Quantity']!=0]
        #print(symbol)
        #print(transaction)
        for out_idx in transaction.index:
            #print(transaction.loc[out_idx])
            require_quant = int(transaction.loc[out_idx,'Quantity'])
            # no storage
            if Q==0:
                Q+=require_quant
            # Flat Storage
            elif Q*require_quant<0:
                in_transaction = transaction.copy()
                in_transaction = in_transaction[in_transaction['TradeDate']<=transaction.loc[out_idx, 'TradeDate']]
                in_transaction = in_transaction[in_transaction['Remain_Quant']!=0]
                idxs = in_transaction.index
                for in_idx in idxs:
                    if require_quant*transaction.loc[in_idx, 'Remain_Quant']>0:
                        continue
                   # print('in: {} out: {}, required quant:{}'.format(in_idx, out_idx, require_quant))
                    trade_quant = int(min(abs(require_quant), abs(transaction.loc[in_idx, 'Remain_Quant'])))
                   # print(trade_quant)
                    require_quant = int((abs(require_quant)-trade_quant)*np.sign(require_quant))
                    transaction.loc[out_idx, 'Remain_Quant'] = int((abs(transaction.loc[out_idx, 'Remain_Quant'])-trade_quant)*np.sign(transaction.loc[out_idx, 'Remain_Quant']))
                    transaction.loc[in_idx, 'Remain_Quant'] = int((abs(transaction.loc[in_idx, 'Remain_Quant'])-trade_quant)*np.sign(transaction.loc[in_idx, 'Remain_Quant'])) 
                    Q = int((abs(Q)-trade_quant)*np.sign(Q))
                    
                    self.buy_sell_pair.loc[len(self.buy_sell_pair)] = {
                        'Symbol':symbol,
                        'Quantity':trade_quant*np.sign(transaction.loc[in_idx, 'Quantity']), 
                        'InIndex':in_idx, 
                        'OutIndex':out_idx,
                        'DateAcquired':transaction.loc[in_idx,'TradeDate'], 
                        'DateSold':transaction.loc[out_idx, 'TradeDate'], 
                        'DaysHeld': (datetime.strptime(transaction.loc[out_idx, 'TradeDate'],"%Y-%m-%d") - datetime.strptime(transaction.loc[in_idx,'TradeDate'], "%Y-%m-%d")).days,
                        'SalesProceeds':abs(transaction.loc[out_idx, 'Price']*trade_quant), 
                        'Cost':abs(transaction.loc[in_idx,'Price']*trade_quant)
                    }

                    if require_quant==0 or Q==0:
                        break
                Q+=require_quant
            # Add storage
            else:
                Q+=require_quant

            #print('remain Q:'+str(Q))
            #print(transaction)
            #print()
            #print()
            for ind in transaction.index:
                self.history.loc[ind,'Remain_Quant'] = transaction.loc[ind,'Remain_Quant']
    
    def output_history(self):
        self.history.to_excel(self.name+"_history.xlsx")

    def output_buy_sell_pair(self):
        self.buy_sell_pair['Total Gain/Loss	'] = self.buy_sell_pair['SalesProceeds'] - self.buy_sell_pair['Cost']
        self.buy_sell_pair.to_excel(self.name+"_Gain_Loss.xlsx")

    @property
    def storage(self):
        df = self.history[self.history['Remain_Quant']!=0].copy()
        df = df[df['RecordType']=='Trade']

        return df
    @property
    def trade_history(self):
        df = self.history.copy()
        df = df.reset_index(drop=True)
        return df[df['RecordType']=='Trade']
    @property
    def stock_value(self):
        if self.cal_stock_value:
            return self.cal_stock_value.copy()
        df = self.trade_history
        df['Quantity'] = df['Quantity'].astype(float)
        df['TradeDate'] = pd.DatetimeIndex(df['TradeDate'])
        daily_trade = df.groupby(['TradeDate','Symbol']).sum()

        
        mux = pd.MultiIndex.from_product([pd.period_range(df['TradeDate'].min(),
                                                  date.today(), freq='D'),
                                                  df['Symbol'].unique()],names=['TradeDate','Symbol'])
        df2 = pd.DataFrame(columns=['Quantity'],index=mux)

        for ind in daily_trade.index:
            day = ind[0]
            symbol = ind[1]
            df2.loc[(day, symbol)] = daily_trade.loc[ind]

        df2['Quantity'] = df2['Quantity'].astype(float)
        df2['Quantity'] = df2['Quantity'].replace(np.nan, 0)
        df2['StorageCount'] = df2['Quantity'].groupby('Symbol').cumsum()
        df2 = df2.reset_index()
        df2 = df2[df2['StorageCount']!=0].copy()
        symbol_list = df['Symbol'].unique()
        price = yf.download(list(symbol_list))

        for i in df2.index:
            day = df2.loc[i,'TradeDate']
            symbol = df2.loc[i, 'Symbol']
            try:
                df2.loc[i,'Price'] = price.loc[day.to_timestamp(), 'Adj Close'][symbol].copy()
            except:
                continue

        df2['MarketValue'] = df2['StorageCount']*df2['Price']
        df2['MarketValue'] = df2['MarketValue'].astype(float)
        df3 = df2.groupby('TradeDate').sum()

        df3 = df3[df3['Price']!=0]
        self.cal_stock_value = df3['MarketValue'].copy()
        return self.cal_stock_value.copy()

    @property
    def cash_flow(self):
        df = self.history
        df = df[df['RecordType']=='Financial']
        df = df[df['Symbol']==""]
        #df = df[df['Action']=='Other']
        money_flow = df.groupby('TradeDate').sum()
        money_flow = money_flow.reset_index()
        return money_flow.copy()
    
    @property
    def dividend(self):
        df = self.history
        df = df[df['Action']=='Dividend']
        dividend = df.groupby('TradeDate').sum()
        dividend = dividend.reset_index()
        return dividend.copy()

    @property
    def cash_balance(self):
        dividend = self.dividend
        cash_flow = self.cash_flow

        df = profolio.history
        df = df[df['RecordType']=='Trade']
        trade = df.groupby('TradeDate').sum()
        trade = trade.reset_index()

        money = pd.concat([trade, dividend, cash_flow], ignore_index=True)
        money = money.groupby('TradeDate').sum()
        money = money.cumsum()
        return money.copy()

if __name__ == '__main__':
    profolio = Profolio('Firstrade')
    profolio.from_csv('data/FT_CSV_87701987.csv')
    print(profolio.stock_value)
    #print(profolio.storage.groupby('Symbol').sum()['Remain_Quant'])