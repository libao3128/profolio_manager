import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
from sqlite3 import Error
import yfinance as yf


class Record():
    def __init__(self, data_path=None) -> None:
        self.record = None 
        self.buy_sell_pair = pd.DataFrame(
            columns=['Symbol','DateAcquired', 'DateSold', 'DaysHeld', 'SalesProceeds', 'Cost', 'Quantity', 'InIndex', 'OutIndex']
        )
        
        if data_path is not None:
            self.data_path = data_path
            self.from_csv(data_path)
        else:
            self.data_path = None
            
    def from_csv(self, file_path: str):
        record = self.record
        df = pd.read_csv(file_path)
        record = pd.concat([record, df])
        record.sort_values(by=['TradeDate'])
        record = record.reset_index(drop=True)
        self.record = record
        
        self.__preprocess()
        
        symbols = self.record['Symbol'].unique()
        for s in symbols:
            self.__build_buy_sell_pair(s)
    
    def __preprocess(self): 
        self.record['Symbol'] = self.record['Symbol'].str.strip()
        self.record = self.record.replace('FB', 'META')
        
        self.record['TradeDate'] = pd.to_datetime(self.record['TradeDate'])
        
    def __build_buy_sell_pair(self, symbol):
        Q = 0
        transaction = Query.TargetTransaction(self.record, target= symbol)
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
                    
                    start_date = pd.to_datetime(transaction.loc[in_idx,'TradeDate'])
                    end_date = pd.to_datetime(transaction.loc[out_idx, 'TradeDate'])
                    DaysHeld = pd.bdate_range(start_date, end_date).size
                    
                    self.buy_sell_pair.loc[len(self.buy_sell_pair)] = {
                        'Symbol':symbol,
                        'Quantity':trade_quant*np.sign(transaction.loc[in_idx, 'Quantity']), 
                        'InIndex':in_idx, 
                        'OutIndex':out_idx,
                        'DateAcquired':transaction.loc[in_idx,'TradeDate'], 
                        'DateSold':transaction.loc[out_idx, 'TradeDate'], 
                        'DaysHeld': DaysHeld,
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
                self.record.loc[ind,'Remain_Quant'] = transaction.loc[ind,'Remain_Quant']


    
    @property
    def start_date(self):
        return self.record['TradeDate'].min()
    
    @property
    def daily_transaction_amount(self):
        data = self.record.copy()
        data = data[['TradeDate', 'Amount']]

        data = data.groupby('TradeDate').sum()
        data.index = pd.to_datetime(data.index)
        
        return data

    @property
    def deposit_transaction(self) -> pd.DataFrame:
        targe_description = 'Wire Funds Received'
        data = self.record.copy()
        # data = data[['TradeDate', 'Amount']]
        #print(data)
        data = data[data['Description'].str.contains(targe_description)]
        #print(data)
        return data.copy()[['TradeDate','Amount']]

class Price():
    def __init__(self, db_path='data/stock_prices.db') -> None:
        self.__conn = Database.create_connection(db_path=db_path)
        self.db_path = db_path
        
    def get_prices(self, symbols:list, columns=['close']):
        if not isinstance(symbols,list): 
            symbols = [symbols]
        columns = ['date','ticker']+columns
          
        prices = pd.DataFrame(columns=columns)
        for s in symbols:
            price = self.__get_price(s, columns)
            if len(price)==0:
                self.update_price(s)
            else:
                latest_date = max(price.index)
                #print(latest_date.date())
                #print(self.__nearest_work_day)
                if latest_date.date() < self.nearest_work_day:
                    import datetime
                    self.update_price(s, start=latest_date + datetime.timedelta(days=1))
                    price = self.__get_price(s, columns)
            
            prices = pd.concat([price, prices])
        return price

    def update_price(self, symbol,start=None,end=None):
        if isinstance(start, pd.Timestamp) and isinstance(end, pd.Timestamp):
            assert start<end, 'Start date should be earlier than end date.'
        
        data = yf.download(symbol,start=start, end=end)
        
        if len(data)==0:
            return
            raise ValueError('Failed to request price date.')
        self.__new_ticket(symbol)
        
        for date, row in data.iterrows():
            try:
                data_tuple = (str(date.date()), symbol, row['Open'], row['High'], row['Low'], row['Close'], row['Adj Close'], row['Volume'])
                Database.insert_data(self.__conn, data_tuple)
            except:
                pass
    
    def __get_price(self, symbol, columns):
        #self.update_price(symbol)
        price = self.__extract_from_database(symbol, columns=columns)
        price = pd.DataFrame(price,columns=columns)
        price = price.set_index('date')
        price.index = pd.DatetimeIndex(price.index)
        
        return price
    
    def __extract_from_database(self, symbol, columns=['close']):
        query = f"SELECT {','.join(columns)} FROM stock_prices WHERE ticker='{symbol}'"
        #query = f"SELECT {','.join(columns)} FROM stock_prices"
        data = Database.select_data(self.__conn, select_query=query)
        return data
    
    def __new_ticket(self, symbol):
        create_table_sql = '''CREATE TABLE IF NOT EXISTS stock_prices (
                        date TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        adj_close REAL NOT NULL,
                        volume INTEGER NOT NULL,
                        PRIMARY KEY (date, ticker)
                     );'''
        Database.create_table(self.__conn, create_table_sql)

    def close_conn(self):
        self.__conn.close()
    
    @property
    def nearest_work_day(self):
        import pandas as pd
        import pandas_market_calendars as mcal
        import datetime as dt
        import pytz
        
        # 创建一个时区对象
        timezone = pytz.timezone('America/New_York')

        # 创建一个市场日历对象
        nyse = mcal.get_calendar('NYSE')

        # 创建一个时区对象
        timezone = pytz.timezone('America/New_York')

        # 获取当前时间
        now = dt.datetime.now(timezone)

        # 查找最近的开盘日
        schedule = nyse.schedule(start_date=(now - dt.timedelta(days=365)).strftime('%Y-%m-%d'), end_date=now.strftime('%Y-%m-%d'))
        
        
       
        
        # 显示最近的开盘日
        #print('过去最近的美股开盘日为：', open_date)
        #print(schedule)
        return schedule.iloc[-1,0].date()


class Database():
    def __init__(self) -> None:
        pass
    
    # 连接到 SQLite 数据库
    @staticmethod
    def create_connection(db_path):
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            print(f'Successfully connected to SQLite database')
        except Error as e:
            print(e)

        return conn
    
    # 创建一个表来存储股价数据
    @staticmethod
    def create_table(conn, create_table_sql):
        try:
            c = conn.cursor()
            c.execute(create_table_sql)
            print('Successfully created table')
        except Error as e:
            print(e)

    # 插入股价数据
    @staticmethod
    def insert_data(conn, data):
        sql = ''' INSERT INTO stock_prices(date, ticker, open, high, low, close, adj_close, volume)
                  VALUES(?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, data)
        conn.commit()
        print(f'Successfully inserted data into table: {data}')

    @staticmethod
    def select_data(conn, select_query):
        cur = conn.cursor()
        cur.execute(select_query)
        rows = cur.fetchall()
        return rows

    @staticmethod
    def is_table_exisit(conn, table_name:str):
        # 创建一个游标对象
        c = conn.cursor()
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        result = c.fetchone()
        return result
class Query():
    
    @ staticmethod
    def TargetTransaction(record: pd.DataFrame, target: str):
        data = record.copy()
        data = Query.TradeTransaction(data)
        return data[data['Symbol']==target]
    
    @staticmethod
    def TradeTransaction(record: pd.DataFrame):
        data = record.copy()
        return data[data['RecordType']=='Trade']

if __name__ == '__main__':
    record = Record('data\FT_CSV_87748402.csv')
    #print(record.buy_sell_pair)
    new_price = Price()
    #print(new_price.get_prices(['AAPL']))
    print(new_price.nearest_work_day)