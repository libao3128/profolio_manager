from datetime import datetime
import pandas as pd
import numpy as np

class Profolio:
    def __init__(self, account_name) -> None:
        self.name = account_name
        self.history = pd.DataFrame(
            columns=['Symbol', 'Quantity', 'Price', 'Action', 'TradeDate', 'Amount', 'RecordType'])
        self.buy_sell_pair = pd.DataFrame(
            columns=['Symbol','DateAcquired', 'DateSold', 'DaysHeld', 'SalesProceeds', 'Cost', 'Quantity', 'InIndex', 'OutIndex']
        )
        self.cash = 0

    def from_csv(self, file):
        df = pd.read_csv(file)
        self.history = pd.concat([self.history, df[self.history.columns]])

        symbols = self.history['Symbol'].unique()
        
        for s in symbols:
            self.__build_buy_sell_pair(s)

    def __build_buy_sell_pair(self, symbol):
        Q = 0
        transaction = self.history[self.history['Symbol']==symbol].copy()
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
    
    def output_history(self):
        self.history.to_excel(self.name+"_history.xlsx")

    def output_buy_sell_pair(self):
        self.buy_sell_pair['Total Gain/Loss	'] = self.buy_sell_pair['SalesProceeds'] - self.buy_sell_pair['Cost']
        self.buy_sell_pair.to_excel(self.name+"_Gain_Loss.xlsx")

if __name__ == '__main__':
    profolio = Profolio('Firstrade')
    profolio.from_csv('FT_CSV_87701987.csv')
    print(profolio.buy_sell_pair['DaysHeld'])