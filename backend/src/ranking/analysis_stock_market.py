import requests
import io
from PIL import Image
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.dates as mdates
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
    
    def analyze_stocks(self, change_stock=0.01):
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
                    'time': data[fields['time']] if fields['time'] < len(data) else None,
                    'price_range': data[fields['high'] - data[fields['low']]],
                }

                if result['change'] > change_stock:
                    result['trend'] = 1
                elif result['change'] < -change_stock:
                    result['trend'] = -1

                if result['price_range'] > data[fields['open']] * 0.01:
                    result['volatility'] = 1
                else:
                    result['volatility'] = 0
                    
                results.append(result)
            except IndexError as e:
                continue
        
        return pd.DataFrame(results)
    
    def plot_separate_charts(self, minutes_back=60, interval=10):
        num_plots = len(self.tickers)
        fig, axes = plt.subplots(num_plots, 1, figsize=(14, 4.5 * num_plots), squeeze=False)
        axes = axes.flatten()

        for idx, ticker in enumerate(self.tickers):
            ax = axes[idx]
            df = self.get_candles(ticker, interval, minutes_back)

            if df is None or df.empty or 'close' not in df.columns or 'begin' not in df.columns:
                ax.set_title(f"{ticker} — данные недоступны")
                continue

            try:           
                df = df.copy()
                df['begin'] = pd.to_datetime(df['begin'], errors='coerce')
                df = df.dropna(subset=['begin'])
                df['change'] = df['close'].diff()
                df['trend'] = df['change'].apply(lambda x: 'up' if x > 0 else 'down')
                df['group'] = (df['trend'] != df['trend'].shift()).cumsum()

                sns.lineplot(
                    data=df,
                    x='begin',
                    y='close',
                    color='gray',
                    linewidth=1,
                    alpha=0.3,
                    ax=ax
                )

                for _, group_df in df.groupby('group'):
                    if len(group_df) < 2:
                        continue
                    color = 'green' if group_df['trend'].iloc[0] == 'up' else 'red'
                    ax.plot(group_df['begin'], group_df['close'], color=color, linewidth=2)

                ax.set_title(f'{ticker}', fontsize=12)
                ax.set_xlabel('Время', fontsize=10)
                ax.set_ylabel('Цена (руб)', fontsize=10)

                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M %d-%m-%Y'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())

                ax.grid(True, linestyle='--', alpha=0.5)

                legend_elements = [
                    Line2D([0], [0], color='green', lw=2, label='Рост'),
                    Line2D([0], [0], color='red', lw=2, label='Падение')
                ]
                ax.legend(handles=legend_elements, fontsize=9)

            except Exception as e:
                ax.set_title(f"{ticker} — ошибка: {e}")

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        im = Image.open(buf)
        return im


moex_stock_analyzer = MoexStockAnalyzer()
print(moex_stock_analyzer.analyze_stocks())
moex_stock_analyzer.plot_separate_charts(minutes_back=3600).show()