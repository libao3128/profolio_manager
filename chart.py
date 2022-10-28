import plotly.express as px
import pandas as pd
import numpy as np

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