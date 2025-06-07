import requests
import io
from PIL import Image
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class MoexStockAnalyzer:
    def __init__(self, tickers=['SBER', 'GAZP', 'LKOH'], board='TQBR'):
        self.tickers = tickers
        self.board = board
        self.base_url = "https://iss.moex.com/iss"
        self.session = requests.Session()
        self.candle_columns = ['open', 'close', 'high', 'low', 'value', 'volume', 'begin', 'end']
        
    def get_market_data(self, ticker):
        try:
            url = f"{self.base_url}/engines/stock/markets/shares/boards/{self.board}/securities/{ticker}.json?iss.only=marketdata"
            response = self.session.get(url, timeout=20).json()
            return response["marketdata"]["data"][0] if response["marketdata"]["data"] else None
        except Exception as e:
            return None
    
    def get_candles(self, ticker, interval=5, minutes_back=15):
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=minutes_back)
            
            url = f"{self.base_url}/engines/stock/markets/shares/boards/{self.board}/securities/{ticker}/candles.json"
            params = {
                'interval': interval,
                'from': start_time.strftime("%Y-%m-%d %H:%M:%S"),
                'till': end_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            response = self.session.get(url, params=params, timeout=10).json()
            
            if not response["candles"]["data"]:
                return None
                
            df = pd.DataFrame(response["candles"]["data"])
            if len(df.columns) == len(self.candle_columns):
                df.columns = self.candle_columns
            return df
            
        except Exception as e:
            return None
    
    def analyze_stocks(self):
        results = []
        for ticker in self.tickers:
            data = self.get_market_data(ticker)
            if data is None:
                continue
                
            fields = {
                'last': 2, 'open': 4, 'high': 10, 'low': 11,
                'change': 14, 'change_prcnt': 15, 'volume': 28,
                'time': 33
            }
            
            try:
                result = {
                    'ticker': ticker,
                    'price': data[fields['last']],
                    'change': data[fields['change']],
                    'change_percent': data[fields['change_prcnt']],
                    'volume': data[fields['volume']],
                    'time': data[fields['time']] if fields['time'] < len(data) else None
                }
                    
                results.append(result)
            except IndexError as e:
                continue
        
        return pd.DataFrame(results)
    
    def plot_separate_charts(self, minutes_back=60, interval=10):
        num_plots = len(self.tickers)
        fig, axes = plt.subplots(num_plots, 1, figsize=(14, 5*num_plots))
        
        if num_plots == 1:
            axes = [axes]
        
        for idx, ticker in enumerate(self.tickers):
            ax = axes[idx]
            df = self.get_candles(ticker, interval, minutes_back)
            if df is None or df.empty:
                continue
                
            if 'close' not in df.columns or 'begin' not in df.columns:
                continue
                
            try:
                df['change'] = df['close'].diff()
                
                sns.lineplot(
                    data=df,
                    x='begin',
                    y='close',
                    color='gray',
                    linewidth=1,
                    alpha=0.3,
                    ax=ax
                )
                
                prev_trend = None
                start_idx = 0
                
                for i in range(1, len(df)):
                    current_trend = 'up' if df['change'].iloc[i] > 0 else 'down'
                    
                    if prev_trend is None:
                        prev_trend = current_trend
                    
                    if current_trend != prev_trend:
                        segment = df.iloc[start_idx:i]
                        color = 'green' if prev_trend == 'up' else 'red'
                        ax.plot(segment['begin'], segment['close'], 
                               color=color, linewidth=2)
                        
                        start_idx = i
                        prev_trend = current_trend
                
                segment = df.iloc[start_idx:]
                color = 'green' if prev_trend == 'up' else 'red'
                ax.plot(segment['begin'], segment['close'], 
                       color=color, linewidth=2)
                
                ax.set_xlabel('Время')
                ax.set_ylabel('Цена (руб)', fontsize=10)
                ax.grid(True, linestyle='--', alpha=0.5)
                
                from matplotlib.lines import Line2D
                legend_elements = [
                    Line2D([0], [0], color='green', lw=2, label='Рост'),
                    Line2D([0], [0], color='red', lw=2, label='Падение')
                ]
                ax.legend(handles=legend_elements, fontsize=9)
                
            except Exception as e:
                continue
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        im = Image.open(buf)
        return im

