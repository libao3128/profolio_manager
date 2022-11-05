import plotly.express as px
import pandas as pd
import numpy as np
import yfinance as yf
from plotly.subplots import make_subplots
from datetime import datetime
from profolio import Profolio
import plotly.graph_objects as go

class Chart:
    def __init__(self, profolio) -> None:
        self.profolio = profolio

    def ROE_DayHeld(self):
        df = self.profolio.buy_sell_pair
        df.columns
        df['ROE'] = (df['SalesProceeds']-df['Cost'])/df['Cost']

        df['DaysHeld'] = df['DaysHeld'].astype(int)
        df['Earn'] = df['ROE']>0
        
        fig = px.scatter(df, x="DaysHeld", y="ROE", color='Earn', 
            color_discrete_map={True:'#EF553B',False: '#00CC96'}, 
            size='Cost',hover_name="Symbol",title='ROE and Day Held', 
            trendline="ols", trendline_scope="overall")

        fig.update_layout(
            yaxis_tickformat = '.2%'
        )
        fig.show()

    def WinRate_GainLose(self):
        df = self.profolio.buy_sell_pair
        df.columns
        df['return'] = df['SalesProceeds'] - df['Cost']
        win = df[df['return']>0]
        lose = df[df['return']<=0]

        win_avg = win.groupby('Symbol').mean()['return']
        lose_avg = lose.groupby('Symbol').mean()['return']
        win_lose_ratio = -win_avg/lose_avg
        win_lose_ratio = win_lose_ratio.replace(np.nan, 0)

        win_cnt = win.groupby('Symbol').count()['return']
        all_cnt = df.groupby('Symbol').count()['return']
        win_rate = win_cnt/all_cnt

        df1 = pd.DataFrame(win_lose_ratio)
        df1['win_rate'] = win_rate.replace(np.nan, 0)
        df1['gain_lose_ratio'] = df1['return']
        df1['count'] = all_cnt
        df1['Symbol'] = df1.index

        fig = px.scatter(df1, x='gain_lose_ratio', y="win_rate", color='Symbol', size='count', size_max=60,hover_name="Symbol",title='Win Rate and Gain Lose Ratio',text="count")
        fig.update_layout(
                    yaxis_tickformat = '.2%'
                )

        fig.show()

    def Monthly_Return(self):
        df = self.profolio.buy_sell_pair
        df['year'] = pd.DatetimeIndex(df['DateSold']).year
        df['month'] = pd.DatetimeIndex(df['DateSold']).month
        df['return'] = df['SalesProceeds'] - df['Cost']
        df1 = df.groupby(by=[df.year, df.month]).sum()
        df1 = df1.reset_index()
        df1['Date'] = pd.to_datetime([f'{y}-{m}-01' for y, m in zip(df1.year, df1.month)])
        df1['color'] = df1['return']>0


        fig1= px.bar(df1, x='Date', y='return', title='Monthly Return', color='color', color_discrete_map={True:'#EF553B',False: '#00CC96'})
        fig1.update_layout(hovermode="x")
        fig1.update_xaxes( tickformat="%b\n%Y")

        fig1.show()

    def ROI_Compare(self, date_range='default', benchmark_name=['^DJI','^GSPC','^IXIC']):
        if date_range == 'default':
            min_date = pd.to_datetime(min(self.profolio.history['TradeDate'])).replace(day=1)
        

        benchmark = yf.download(benchmark_name)
        benchmark = pd.DataFrame(benchmark['Adj Close'])
        benchmark.index = pd.DatetimeIndex(benchmark.index)

        pair = self.profolio.buy_sell_pair
        pair['return'] = pair['SalesProceeds'] - pair['Cost']
        Return = pd.DataFrame(pair.groupby('DateSold').sum(numeric_only=False)['return'])
        Return.index=pd.DatetimeIndex(Return.index)
        history = self.profolio.history
        In = history[history['Action']=='Other']
        In = In.groupby('TradeDate').sum(numeric_only=False)
        In = In[In['Amount']>0] 
        In.index = pd.DatetimeIndex(In.index)

        benchmark['return'] = Return['return']
        benchmark['In'] = In['Amount']
        benchmark = benchmark.replace(np.nan, 0)
        benchmark['return'] = benchmark['return'].cumsum()
        benchmark['In'] = benchmark['In'].cumsum()

        benchmark['total'] = benchmark['return'] + benchmark['In']
        benchmark['ROI'] = benchmark['total'] / benchmark['In']
        benchmark = benchmark.replace(np.nan, 1)

        fig = make_subplots(
            rows=2, cols=1,
            row_width=[0.3, 0.7],
            start_cell="top-left",
            subplot_titles=['ROI Comparison'],
            shared_xaxes=True,vertical_spacing=0.05)
        fig.add_scatter(y= benchmark[benchmark.index>=min_date]['ROI'],
            x=benchmark[benchmark.index>=min_date].index, 
            row=1, col=1, name='Profolio',
            line=dict(color=px.colors.qualitative.Plotly[1]))
       
        for i,col in enumerate(benchmark_name):
            df = benchmark[benchmark.index>=min_date].copy()
            df.loc[:,col] = df.loc[:,col]/df.loc[:,col].iloc[0]
            fig.add_scatter(y= df.loc[:,col],x=df.index, row=1, col=1, 
                name=col,line=dict(color=px.colors.qualitative.Pastel1[i]))

        
        #fig.add_scatter(y= df['cummulative_return_rate'],x=df.index, row=1, col=1, name='ROI')
        fig.update_traces(mode="lines", hovertemplate=None)
        fig.update_layout(xaxis_title="", yaxis_title="ROI", yaxis_tickformat = '.2%')
        fig.update_xaxes(title='x', visible=False, showticklabels=False, row=1, col=1)
        fig.update_layout(hovermode="x")
        fig.update_layout(legend_title_text='ROI')
        fig.add_bar(y=Return[Return['return']>=0]['return'],x=Return[Return['return']>=0]['return'].index,marker={'color':'#EF553B'}, row=2, col=1,name='earn', showlegend=False)
        fig.add_bar(y=Return[Return['return']<0]['return'],x=Return[Return['return']<0].index,marker={'color':'#00CC96'}, row=2, col=1,name='lost', showlegend=False)
        fig.show()

    def Storage_Share(self):
        storage = self.profolio.storage
        #print(storage['Quantity'])
        #print(storage['Remain_Quant'])
        #print(storage.groupby('Symbol').sum(numeric_only=False))

        storage = storage.groupby('Symbol').sum(numeric_only=False)['Quantity'].sort_values(ascending=False)
        
        storage.index = storage.index.str.strip()
        storage = pd.DataFrame(storage[storage>0])


        price = yf.download(list(storage.index),start=datetime.now())

        storage['price'] = price['Adj Close'].iloc[0]
        storage['market_value'] = storage['price']*storage['Quantity']
        storage = storage.reset_index()

        fig = px.pie(storage, 'Symbol', 'market_value', title='Storage Market Value Share')
        fig.show()

    def Total_Value(self):
        cash = pd.DataFrame(self.profolio.cash_balance)
        stock = pd.DataFrame(self.profolio.stock_value)

        min_date = pd.to_datetime(min(min(cash.index),min(stock.index)))
        max_date = datetime.today()
        idx = pd.date_range(min_date, max_date)
        cash = cash.reindex(idx, method='ffill')
        stock = stock.reindex(idx, method='ffill')

        cash['Balance'] = 'cash'
        cash.columns = ['Value', 'Balance']
        cash = cash.fillna(0)
        stock['Balance'] = 'stock'
        stock.columns = ['Value', 'Balance']
        stock = stock.fillna(0)

        df = pd.concat([cash,stock],axis=0)

        df = pd.concat([cash,stock],axis=0)
        #df = df.fillna(method='ffill')
        #df = df.fillna(0)

        df = df.reset_index()
        df.columns = ['Date', 'Value', 'Balance']
        fig = px.area(
            df, x='Date', y='Value', color='Balance', 
            hover_name='Balance', title='Total Value Chart',
            hover_data={
            'Balance':False,
            'Date':False,
            'Value':':.1f'
        })
        #self.__add_benchmark(fig, [min_date])
        fig.update_layout(legend_title_text='Balance')
        fig.update_layout(hovermode="x")
        fig.update_traces(connectgaps=True)
        fig.show()

    def __add_benchmark(self, fig, date_range,benchmark_name=['^DJI','^GSPC','^IXIC']):
        benchmark = yf.download(benchmark_name)
        benchmark = pd.DataFrame(benchmark['Adj Close'])
        benchmark.index = pd.DatetimeIndex(benchmark.index)

        for i,col in enumerate(benchmark_name):
            df = benchmark[benchmark.index>=date_range[0]].copy()
            df.loc[:,col] = df.loc[:,col]/df.loc[:,col].iloc[0]
            fig.add_trace(
                go.Scatter(y= df.loc[:,col],x=df.index, 
                name=col,line=dict(color=px.colors.qualitative.Pastel1[i])),
                secondary_y=True,
            )
    
if __name__ == '__main__':
    profolio = Profolio('Firstrade')
    profolio.from_csv('data/FT_CSV_87701987.csv')
    new_chart = Chart(profolio)
    #new_chart.ROE_DayHeld()
    #new_chart.WinRate_GainLose()
    #new_chart.Monthly_Return()
    new_chart.ROI_Compare()
    #new_chart.Storage_Share()