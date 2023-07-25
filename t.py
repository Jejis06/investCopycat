import yfinance as yf
from datetime import datetime, timedelta




def deltaprice(start, end, stock):
    ticker = yf.Ticker('TSLA')

    start = start.strftime('%Y-%m-%d') 
    end = end.strftime('%Y-%m-%d') 

    df = ticker.history(interval='1d', start = start, end = end)


    print('current',df['Close'].iloc[-1])
    print('last',df["Close"].iloc[0])

