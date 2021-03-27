import ccxt
import time
import json
import requests
import decimal
from slacker import Slacker
from slack import WebClient
from slack.errors import SlackApiError
from datetime import datetime, timedelta
from pandas.io.json import json_normalize

#batchSize = 100
#winCount = 0
#buyCount = 0

#WEEKNUM = 1
#DAYNUM = 3

#ubuntuTimeDelta = 3600*9
#jet_lag = timedelta(hours=9)
#week = timedelta(weeks=WEEKNUM)
#day = timedelta(days=DAYNUM)

#refer_date = datetime.today() - (week+day) + jet_lag
#quarterHourNum = 4 * 24 * (WEEKNUM * 7 + DAYNUM)
#since = binance.parse8601(refer_date.strftime('%Y-%m-%dT%H:%M:%SZ'))

def float_to_decimal(f):
    # http://docs.python.org/library/decimal.html#decimal-faq
    "Convert a floating point number to a Decimal with no loss of information"
    n, d = f.as_integer_ratio()
    numerator, denominator = decimal.Decimal(n), decimal.Decimal(d)
    ctx = decimal.Context(prec=60)
    result = ctx.divide(numerator, denominator)
    while ctx.flags[decimal.Inexact]:
        ctx.flags[decimal.Inexact] = False
        ctx.prec *= 2
        result = ctx.divide(numerator, denominator)
    return result

def f(number, sigfig):
    # http://stackoverflow.com/questions/2663612/nicely-representing-a-floating-point-number-in-python/2663623#2663623
    assert(sigfig>0)
    try:
        d=decimal.Decimal(number)
    except TypeError:
        d=float_to_decimal(float(number))
    sign,digits,exponent=d.as_tuple()
    if len(digits) < sigfig:
        digits = list(digits)
        digits.extend([0] * (sigfig - len(digits)))
    shift=d.adjusted()
    result=int(''.join(map(str,digits[:sigfig])))
    # Round the result
    if len(digits)>sigfig and digits[sigfig]>=5: result+=1
    result=list(str(result))
    # Rounding can change the length of result
    # If so, adjust shift
    shift+=len(result)-sigfig
    # reset len of result to sigfig
    result=result[:sigfig]
    if shift >= sigfig-1:
        # Tack more zeros on the end
        result+=['0']*(shift-sigfig+1)
    elif 0<=shift:
        # Place the decimal point in between digits
        result.insert(shift+1,'.')
    else:
        # Tack zeros on the front
        assert(shift<0)
        result=['0.']+['0']*(-shift-1)+result
    if sign:
        result.insert(0,'-')
    return ''.join(result)

#https://khream.tistory.com/8 binance api 함수정리
binance = ccxt.binance({
    'apiKey': 'symvImMQbg7faWx7Bx4XEAIVhPkVY4OJBWvWSNqAuXJpD7Hk3mzMiCPJx01t95kZ',
    'secret': 'xrDjxb10kdMSLUdMjSgxmQUX9U0KKILiawEWvkqAVed7dTEksyFdiRhAS2iHQhpn',
})
market = binance.load_markets()
balance = binance.fetch_balance()


#count = 0
wallet = []

token = 'xoxb-1803312053650-1803316179538-RdYSfXZjfyEvrkwtv2KRVucC'
channel_id = "C01PTELKWAG"
client = WebClient(token=token)


SEEDMONEY = balance['BTC']['total']
MinCoinNum = market['ETH/BTC']['limits']['amount']['min'] * 6 ##?? 살 수 있는데 왜 못 사는거니 ㅠㅠㅠㅠ
#binance.create_market_sell_order('ETH/BTC', 0.024)
print("SEEDMONEY:", f(SEEDMONEY, 4))
print("살 수있는 최소 코인 갯수", MinCoinNum)
#binance.create_market_buy_order('ETH/BTC', 0.006)



ohlcvs = binance.fetch_ohlcv('ETH/BTC', '1m', limit=20)
while True:
    current_price = ohlcvs[-1][4]
    current_volume = ohlcvs[-1][5]
    volume_average = sum([ohlc[5] for ohlc in ohlcvs[-15:]]) / len(ohlcvs[-15:])

    if len(wallet) != 0:
        for price in wallet:
            if current_price >= price * 1.005:
                try:
                    binance.create_market_sell_order('ETH/BTC', MinCoinNum)
                    wallet.remove(price)
                    print("이득봄 ㅎ")
                    response = client.chat_postMessage(
                        channel=channel_id,
                        text="승호가 이더리움 {} 개를 팔아서 {} BTC만큼 벌었어요!!".format(MinCoinNum, f((current_price - price) * MinCoinNum, 2))
                    )
                except:
                    print("에러남")
                    response = client.chat_postMessage(
                        channel=channel_id,
                        text="에러남"
                    )
            
    if current_volume > volume_average * 2:
        try:
            current_price = binance.fetch_ticker('ETH/BTC')['close']
            binance.create_market_buy_order('ETH/BTC', MinCoinNum)
            wallet.append(current_price)
            print("샀음 ㅎ")
            response = client.chat_postMessage(
                channel=channel_id,
                text="승호가 {} ETH/BTC에 이더리움 코인을 {} 개 만큼 샀어요!!".format(current_price, MinCoinNum)
            )
        except:
            print("돈이가 없거나 최소 주문가능금액보다 적게삼")
    
    time.sleep(60)
    
    try:
        ohlc = binance.fetch_ohlcv('ETH/BTC', '1m', limit=1)
        ohlcvs += ohlc
        del ohlcvs[0]
    except:
        print('api 요청 에러')
        response = client.chat_postMessage(
                        channel=channel_id,
                        text='api 요청 에러'
                    )
        time.sleep(600)
        ohlc = binance.fetch_ohlcv('ETH/BTC', '1m', limit=10)
        ohlcvs += ohlc
        del ohlcvs[:10]

'''
백테스팅용
while count < batchSize:
    ohlcvs = binance.fetch_ohlcv('ETH/BTC', '15m', since, limit=quarterHourNum)
    ohlcvs = ohlcvs[:-batchSize+count]
    current_price = ohlcvs[-1][4]
    current_volume = ohlcvs[-1][5]
    price_average = (sum([ohlc[4] for ohlc in ohlcvs]) - current_price)/(len(ohlcvs)-1)
    volume_average = (sum([ohlc[5] for ohlc in ohlcvs]) - current_volume)/(len(ohlcvs)-1)
    if current_volume > volume_average * 2:
        
        buy = True
        buyCount += 1

    count += 1
    if buy:
        ohlcvs = binance.fetch_ohlcv('ETH/BTC', '15m', since, limit=quarterHourNum)
        ohlcvs = ohlcvs[:-batchSize+count]
        next_price = ohlcvs[-1][4]
        
        
        buy = False
        if next_price > current_price * 1.0001:
            winCount += 1
'''
#print("시드머니 = ", SEEDMONEY + sum(wallet))

#try:
    #print("단타로 딸 확률", round(winCount/buyCount * 100, 2), "%")
#except ZeroDivisionError:
    #print("no buy")
#print("산 횟수: ", buyCount)
