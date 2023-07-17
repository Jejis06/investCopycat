import requests as rq 
import json
import os
from datetime import datetime
import time
import yfinance as yf

# txType=buy&txType=sell&mcap=6&mcap=5&mcap=4&mcap=2&mcap=3

class Trader:
    def __init__(self):

        self.baseUrl = "https://bff.capitoltrades.com/trades?sortBy=-pubDate"
        self.txTypeBuy = "txType=buy"
        self.txTypeSell = "txType=sell"
        self.sep = "&"
        self.mcap = 2 # from 2 to 7
        self.page = 1
        self.spage = "page="

        return

    def getHistoricalGain(self, startTime, stock):
        ticker = yf.Ticker(stock)
        currentPrice= ticker.info['currentPrice']
        print(data)
        

    def getData(self, pageId):
        url = f"{self.baseUrl}{self.sep}{self.spage}{pageId}{self.sep}{self.txTypeBuy}{self.sep}{self.txTypeSell}"
        res = rq.get(url)

        obj = json.loads(res.content.decode('utf-8'))

        # parse by date
        now = datetime.now()
        for pitch in obj["data"]:
            txDate = datetime.strptime(pitch["txDate"], '%Y-%m-%d')
            deltaTime = (now - txDate).days
            print(deltaTime)
        
        return


    def test(self):
        self.getData(1)
        return




def main():
    os.system("clear")
    tr = Trader()
    tr.test()

    return

if __name__ == "__main__":
    main()
