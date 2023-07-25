import re
import yfinance as yf
from datetime import datetime, timedelta
import json




def deltaprice(start, end, stock):
    ticker = yf.Ticker('TSLA')

    start = start.strftime('%Y-%m-%d') 
    end = end.strftime('%Y-%m-%d') 

    df = ticker.history(interval='1d', start = start, end = end)


    print('current',df['Close'].iloc[-1])
    print('last',df["Close"].iloc[0])


def read():
    with open("d.json", "r") as f:
        print(json.load(f))
read()
