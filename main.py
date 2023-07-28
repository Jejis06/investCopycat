import requests as rq 
import json
import os
from datetime import datetime
import yfinance as yf
import copy
import schedule
import time 
import argparse


def make_hash(o):
  if isinstance(o, (set, tuple, list)):

    return tuple([make_hash(e) for e in o])

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))


SAVE_FILE = "db.json"
HISTORY_FILE = "history.json"


class Trader:
    def save(self):
        save = {
                "balance" : self.balance,
                "hashedHoldings" : self.hashedHoldings,
                "holdings" : self.holdings,
                "holdingsNames" : self.holdingsOnlyNames
        }

        with open(SAVE_FILE, 'w') as f:
            json.dump(save, f, indent=6)
            f.close()

        return

    def load(self):
        try:
            with open(SAVE_FILE, "r") as f:
                save = json.load(f)
                f.close()
        except: return

        self.balance = save["balance"] 
        self.hashedHoldings = save["hashedHoldings"] 
        self.holdings = save["holdings"] 
        self.holdingsOnlyNames = save["holdingsNames"] 

        return
        
    def __init__(self):

        # balance to test trades in usd 
        self.balance = 1000

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

        # history
        self.history = []

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

        # max time allowed between purnchase and today
        self.maxAvgDtime = 60

        # safechecks
        self.ACCEPTANCE_LEVEL = self.ACCEPTANCE_LEVEL % (self.VALUE_TABLE_SIZE + 1)

        self.load()
        return

    def stockPrice(self, stock):
        return int(yf.Ticker(stock).info['currentPrice'])

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
        print(tradeEval)

        tradeHash = make_hash(trade)

        if (generalEvalInt > self.ACCEPTANCE_LEVEL) or (gain * 100 < 0): return 1
        if tradeHash in self.hashedHoldings: return -1



        if (txType == 'sell') and (ticker in self.holdingsOnlyNames):
            self.bet.append((trade, (tradeEval, tradeHash)))
            
        if (txType == 'buy') and (ticker not in self.holdingsOnlyNames):
            self.bet.append((trade, (tradeEval, tradeHash)))


        return 2


        

    def getData(self, pageId, ammPages = False):
        url = f"{self.baseUrl}{self.sep}{self.spage}{pageId}{self.sep}{self.txTypeBuy}{self.sep}{self.txTypeSell}"

        try: res = rq.get(url)
        except: return (1, 0.1)


        obj = json.loads(res.content.decode('utf-8'))
        if ammPages: 
            return (int(obj["meta"]["paging"]["totalPages"]),0.1)

        # parse by date
        now = datetime.now()
        avgDtime = 0

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
                avgDtime += dTime

                print("Dtime : ", dTime)
                print(f"{ticker} -- {issuer} : {txType}")
                print(dTime, "days")
                print(f"Gain {gain:.1%}")
                print(f"price {value} | owner {owner}")
                print(f"By : {politician}")
                flag = self.tradeOrganizer(dTime, txDate, ticker, issuer, txType, politician, value, owner, gain)

                if flag > 1: print("\t\tAccepted")
                else: print("Rejected")

                print()

                if flag < 0:
                   print('[ALL NEW DATA SCRAPED]')
                   return (1, avgDtime/len(obj['data'])) 

        return (-1, avgDtime/len(obj['data'])) 

    def pitch(self):
        # Dummy function to ask user if trades are acceptable
        # Returns how much pitches have been accepted by user 
        # (for now everything is accepted)

        self.txQueue += self.bet
        self.bet.clear()
        return len(self.txQueue) 


    def classifyAmm(self, invested):
        classified = 100

        if invested < 1_000:
            classified = 10
        elif invested < 15_000:
            classified = 20
        elif invested < 50_000:
            classified = 30
        elif invested < 100_000:
            classified = 40
        elif invested < 250_000:
            classified = 40
        elif invested < 500_000:
            classified = 50
        elif invested < 1_000_000:
            classified = 60
        elif invested < 5_000_000:
            classified = 70
        elif invested < 25_000_000:
            classified = 80
        elif invested < 50_000_000:
            classified = 90

        return classified/100

    def buyStock(self, transaction):

        if self.balance <= 0: return
        #self.holdingsOnlyNames

        stock = transaction[0]['ticker']
        price = self.stockPrice(stock)

        if stock in self.holdingsOnlyNames: return None

        budget = self.balance * self.classifyAmm(transaction[0]['value'])
        ammBought = budget / price
        self.balance -= budget

        print(f"[BUY] Stock: {stock} bought for {budget} | balance before: {self.balance+budget} | balance after: {self.balance}")

        history = {
                'stock':stock,
                'ammBought':ammBought,
                'balanceBefore':self.balance+budget,
                'balanceAfter':self.balance
        }
        self.holdings.append({
            "stock" : stock,
            "ammBought": ammBought
        })
        self.holdingsOnlyNames.append(stock)
        self.hashedHoldings.append(transaction[1][1])

        return history

    def sellStock(self, transaction):
        stock = transaction[0]['ticker']
        price = self.stockPrice(stock)

        for i in self.holdings.copy():
            if i['stock'] == stock:
                gained = price * i['ammBought']
                self.balance += gained

                print(f"[SELL] Stock: {stock} sold for {gained} | balance before: {self.balance-gained} | balance after: {self.balance}")
                history = {
                        'stock':stock,
                        'gained':gained,
                        'balanceBefore':self.balance  - gained,
                        'balanceAfter':self.balance
                }

                self.holdings.pop(self.holdings.index(i))
                self.holdingsOnlyNames.pop(self.holdingsOnlyNames.index(stock))
                return history

        return None


    def commitTransactions(self):
        print(len(self.txQueue))
        for transaction in self.txQueue:
            if transaction[0]['txType'] == 'buy': 
                o = self.buyStock(transaction)
            else: 
                o = self.sellStock(transaction)

                if o != None:
                    self.history.append(o)
        self.txQueue.clear()

        return

    def scrape(self):
        ammPages = self.getData(1, ammPages=True)[0]
        for i in range(1,ammPages):
            res = self.getData(i)
            print(f"\t\tPage : {i} / avgDtime : {res[1]}")

            if res[0] > 0 or res[1] >= self.maxAvgDtime: break
             

        if len(self.bet) > 0: self.pitch()
        print("commiting transactions : ")
        self.commitTransactions()
        print("saving history snapshot")
        self.saveSnapshot()
        print("saving")
        self.save()
        print(f"TODAYS BALANCE {self.balance}")


    def timedRun(self, runTime):
        schedule.every().day.at(runTime).do(self.scrape)

        while True:
            schedule.run_pending()
            time.sleep(1)


    def test(self):
        self.scrape()
        return

    def saveSnapshot(self):
        if len(self.history) == 0: return
        now = time.time()
        with open(SAVE_FILE, 'a') as f:
            f.write("{" + f"{now}:" + str(self.history) + "},\n")
            f.close()
        self.history = []




def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--test', action='store_true')
    args = parser.parse_args().test

    os.system("clear")
    tr = Trader()
    if args == True:
        tr.test()
    else:
        tr.timedRun("10:00")

    return

if __name__ == "__main__":
    main()
