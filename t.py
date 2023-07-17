import yfinance as yf
import datetime

tickerSymbol = 'AMD'

tickerData = yf.Ticker(tickerSymbol)
todayData = tickerData.info['currentPrice']

s = datetime.datetime.now() 
e = s

delta = datetime.timedelta(days = 30)

s -= delta
e -= delta - datetime.timedelta(days=1)

s = s.strftime('%Y-%m-%d')
e = e.strftime('%Y-%m-%d')

# dataBack = tickerData.history(start=s,end=e)
dataBack = tickerData.history(period='1y')


print(dataBack)
print(todayData) 

