# modules/plotter.py
import plotly.express as px
import pandas as pd

class ETFVisualizer:
    @staticmethod
    def plot_comparison(combined_df: pd.DataFrame):
        """
        將多支ETF的時間序列資料繪製成折線圖。
        要求: combined_df 需包含 'Date', 'Close', 'ETF_Code' 欄位。
        """
        if combined_df.empty:
            print("沒有可繪圖的資料")
            return
        
        fig = px.line(
            combined_df,
            x='Date',
            y='Close',
            color='ETF_Code',
            title='ETF Performance Comparison'
        )
        fig.update_xaxes(rangeslider_visible=True)
        return fig
