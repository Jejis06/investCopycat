import requests as rq 
import json
import os
from datetime import datetime
import time
import yfinance as yf
import copy

def make_hash(o):
  if isinstance(o, (set, tuple, list)):

    return tuple([make_hash(e) for e in o])

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))




class Trader:
    def __init__(self):

        # url values
        self.baseUrl = "https://bff.capitoltrades.com/trades?sortBy=-pubDate"
        self.txTypeBuy = "txType=buy"
        self.txTypeSell = "txType=sell"
        self.sep = "&"
        self.mcap = 2 # from 2 to 7
        self.page = 1
        self.spage = "page="


        # list of hashes of scraped data so the bot doesnt buy the same thing 
        self.hashedHoldings = [] 

        # transactions that are going to be made (sells/buys)
        self.txQueue = []

        # current purnchased stocks
        self.holdings = []
        self.holdingsOnlyNames = []

        # stocks waiting for confirmation
        self.bet = []

        # how many days since the transaction is considered to be still valuable
        self.SAFE_TIMESPAN = {
                "safe":20,
                "moderate":30,
                "risky":40,
        }
        # multiplier that yelds how different family members should be treated ( the higher the more important )
        self.OWNERS = {
                "spouse" : 0.3 ,
                "child" : 0.1,
                "not-disclosed" :0.1 ,
                "joint" : 0.2 ,
                "self" : 0.1,
        }
        # how much capitol gained for the politicians is risky
        self.SAFE_GAINS_PERC = {
                "safe" : 10,
                "moderate" : 20,
                "risky" : 30,

        }

        # how much is gain percentage important for the evaluation
        self.GAIN_IMPORTANCE = 1
        # how much time between today and last time of transaction is important for the evaluation
        self.TIME_IMPORTANCE = 1.3

        # table of evaluation levels
        self.VALUE_TABLE = {
                "safe" : 1,
                "moderate" : 2,
                "risky" : 3,
        }
        self.VALUE_TABLE_SIZE = len(list(self.VALUE_TABLE.keys()))

        # what level of evaluation is accepted
        self.ACCEPTANCE_LEVEL = 2


        # safechecks
        self.ACCEPTANCE_LEVEL = self.ACCEPTANCE_LEVEL % (self.VALUE_TABLE_SIZE + 1)
        return

    def getHistoricalGain(self, start, end, stock):

        ticker = yf.Ticker(stock)

        start = start.strftime('%Y-%m-%d')
        end = end.strftime('%Y-%m-%d')

        df = ticker.history(interval='1d', start = start, end = end)


        currentPrice = df["Close"].iloc[-1]
        historicalPrice = df["Close"].iloc[0]

        return (currentPrice - historicalPrice) / historicalPrice


        
    # work work work
    def tradeOrganizer(self, dTime, txDate, ticker, issuer, txType, politician, value, owner, gain):

        Tprob = "risky"
        for key, value in self.SAFE_TIMESPAN.items():
            if dTime <= value: Tprob = key ; break

        Gprob = "risky"
        for key, value in self.SAFE_GAINS_PERC.items():
            if int(gain * 100)<= value: Gprob = key ; break

        generalEvalInt = round(
            (self.VALUE_TABLE[Gprob] * self.GAIN_IMPORTANCE + self.VALUE_TABLE[Tprob] * self.TIME_IMPORTANCE) / (2 + self.OWNERS[owner])
        ) % (self.VALUE_TABLE_SIZE)
        if generalEvalInt == 0: generalEvalInt = self.VALUE_TABLE_SIZE

        generalEvalStr = list(self.VALUE_TABLE.keys())[
                list(self.VALUE_TABLE.values()).index(
                    generalEvalInt
                ) 
        ]

        trade = {
                "txType" : txType,
                "txDate" : txDate,
                "ticker" : ticker,
                "issuer" : issuer,
                "politician" : politician,
                "owner" : owner,
                "gain" : gain * 100,
                "value" : value,

        }
        tradeEval = {
                "timeEval" : Tprob,
                "priceEval" : Gprob,
                "generalEval" : {"str" : generalEvalStr, "int" : generalEvalInt} 

        }

        tradeHash = make_hash(trade)

        if (generalEvalInt >= self.ACCEPTANCE_LEVEL) or (gain * 100 < 0): return 1
        if tradeHash in self.hashedHoldings: return -1



        if (txType == 'sell') and (ticker in self.holdingsOnlyNames):
            self.bet.append((trade, tradeEval))
            
        if txType == 'buy':
            self.bet.append((trade, tradeEval))

        return 1


        

    def getData(self, pageId, ammPages = False):
        url = f"{self.baseUrl}{self.sep}{self.spage}{pageId}{self.sep}{self.txTypeBuy}{self.sep}{self.txTypeSell}"
        res = rq.get(url)


        obj = json.loads(res.content.decode('utf-8'))
        if ammPages: 
            return int(obj["meta"]["paging"]["totalPages"])

        # parse by date
        now = datetime.now()
        for pitch in obj["data"]:
            if pitch['asset']['assetType'] == 'stock':

                txDate = datetime.strptime(pitch["txDate"], '%Y-%m-%d')
                ticker = pitch['asset']['assetTicker'].split(":")[0]
                issuer = pitch['issuer']['issuerName']
                txType = pitch["txType"]
                politician = pitch["politician"]
                value = pitch['value']
                owner = pitch['owner'] # spouse, child

                try: gain = self.getHistoricalGain(txDate, now, ticker)
                except: continue

                dTime = (now - txDate).days

                print(dTime)
                
                print(f"{ticker} -- {issuer} : {txType}")
                print(dTime, "days")
                print(f"Gain {gain:.1%}")
                print(f"price {value} | owner {owner}")
                print(f"By : {politician}")
                flag = self.tradeOrganizer(dTime, txDate, ticker, issuer, txType, politician, value, owner, gain)
                print()

                if flag < 0:
                   print('[ALL NEW DATA SCRAPED]')
                   return 1 
        
        return -1


    def scrape(self):
        ammPages = self.getData(1, ammPages=True)
        print(ammPages)
        for i in range(1,ammPages):
            print("\t\t",i)
            self.getData(i)


        print(self.bet)
        print(len(self.bet))


    def test(self):
        self.scrape()
        return




def main():
    os.system("clear")
    tr = Trader()
    tr.test()

    return

if __name__ == "__main__":
    main()
