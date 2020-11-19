#!/usr/bin/python2.7
#TODO UPDATE CAO: 4/1/18
# Requires python-requests. Install with pip:
#
#   pip install requests
#
# or, with easy-install:
#
#   easy_install requests
#Blog post from which much of this code was copied:
#https://cryptostag.com/basic-gdax-api-trading-with-python/

#Note the GDAX crypto ids are as follows:
'''
BTC-USD
BTC-GBP
BTC-EUR
ETH-BTC
ETH-USD
LTC-BTC
LTC-USD
ETH-EUR
LTC-EUR
BCH-USD
BCH-BTC
BCH-EUR
'''

import json, hmac, hashlib, time, requests, base64, sys, os, signal, math #numpy
from datetime import datetime, timedelta
from requests.auth import AuthBase
from collections import deque
#==============================================================================
#Global variable(s)
gStopFlag = False
gProductIDs = [
'BTC-USD',
'ETH-USD',
'LTC-USD',
'BCH-USD'
]
gGranularity = [60, 300, 900, 3600, 21600, 86400]
gRevGranularity = [86400, 21600, 3600, 900, 300, 60]

    #Set the granularity in seconds based on the timeframe
    #btc_1hr_trend = deque()   #60 records, 1 per minute
    #btc_1d_trend  = deque()   #288 recores, 1 per 5 minutes
    #btc_7d_trend  = deque()   #168 records, 1 per hour
    #btc_30d_trend = deque()   #723 records, 1 per hour
gTimeframeToGranularity = {'1hr':60,'1d':300,'7d':3600,'30d':3600}
gTimeframeToHourDelta = {'1hr':1,'1d':24,'7d':168,'30d':210}
gFieldToIndex = { 'low' : 1, 'high' : 2, 'open': 3, 'close' : 4 }

#==============================================================================
#This function flips a global flag indicating an exit condition - graceful quit
def signal_handler(signal, frame):
    global gStopFlag
    gStopFlag = True    
    print('Caught Interrupt signal.  Exiting!')
        
#==============================================================================
# Create custom authentication for Exchange
class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = signature.digest().encode('base64').rstrip('\n')

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

#==============================================================================
#Returns a list of products from the exchange
def products():
    response = requests.get(api_base + '/products')
    # check for invalid api response
    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    return response.json()
#==============================================================================
#Function for executing market buy order - possibly not needed
def market_buy(product_id, size):
    auth = GDAXRequestAuth(api_key, api_secret, passphrase)
    order_data = {
        'type': 'market',
        'side': 'buy',
        'product_id': product_id,
        'size': size
    }
    response = requests.post(api_base + '/orders', data=json.dumps(order_data), auth=auth)
    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    return response.json()
#==============================================================================
#Return the status of the order with the given ID #
def order_status(order_id):
    order_url = api_base + '/orders/' + order_id
    response = requests.get(order_url, auth=auth)
    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    return response.json()
#==============================================================================
#Execute limit buy order
def limit_buy(product_id, price, size, time_in_force='GTC', \
    cancel_after=None, post_only=None):

    auth = GDAXRequestAuth(api_key, api_secret, passphrase)
    order_data = {
        'type': 'limit',
        'side': 'buy',
        'product_id': product_id,
        'price': price,
        'size': size,
        'time_in_force': time_in_force
    }
    if 'time_in_force' is 'GTT':
        order_data['cancel_after'] = cancel_after 
    if 'time_in_force' not in ['IOC', 'FOK']:
        order_data['post_only'] = post_only
    response = requests.post(api_base + '/orders', data=json.dumps(order_data), auth=auth)
    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    return response.json()
#==============================================================================
#https://docs.gdax.com/#orders
#Generic order function, can handle buy/sell and market/limit orders
def submit_order(order_type, side, product_id, price, size, \
    time_in_force='GTC', cancel_after=None, post_only=None):

    auth = GDAXRequestAuth(api_key, api_secret, passphrase)
    order_data = {
        'type': order_type,                      #market or limit   
        'side': side,                            #buy or sell
        'product_id': product_id,
        'price': price,
        'size': size,
        'time_in_force': time_in_force
    }
    if 'time_in_force' is 'GTT':
        order_data['cancel_after'] = cancel_after 
    if 'time_in_force' not in ['IOC', 'FOK']:
        order_data['post_only'] = post_only
    response = requests.post(api_base + '/orders', data=json.dumps(order_data), auth=auth)
    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    return response.json()

#==============================================================================
def getHistoricRate(api_url, product_id, start, end, granularity):
    #Returns a list of lists:
    '''
    [
        [ time, low, high, open, close, volume ],
        [ 1415398768, 0.32, 4.2, 0.35, 4.2, 12.3 ],
         ...
    ]
    '''
    #Enable access to globals
    global gProductIDs, gRevGranularity
        
    #Error checking
    if product_id not in gProductIDs:
        print "Error in getHistoricRate: 'product_id' is", product_id, "which is not valid."
        return -1
    if not isinstance(start, datetime):
        print "Error in getHistoricRate: 'start' is not a datetime object."
        return -2
    if not isinstance(end, datetime):
        print "Error in getHistoricRate: 'end' is not a datetime object."
        return -3

    #Calculate requested time frame and # of data points
    timeRange = end - start
    timeRange = int(timeRange.total_seconds())
    #print timeRange
    candles = timeRange / granularity
    #print 'Time range (seconds) of request:', timeRange
    #print "Candles:",candles
    
    #If granularity is not valid, or if # of candles > 300, 
    #find the smallest valid granularity value for the time frame and use that
    #granularity instead
    if granularity not in gRevGranularity or candles > 300:
        print granularity, ' is invalid, it would result in ', candles, ' candles'
        #Calulate best granularity based on time frame
        for g in gRevGranularity:
            #print "Considering ",g, " as a possible granularity"
            candles = int(timeRange / g)
            #print "This would result in ", candles, " candles"
            if candles < 300:
                granularity = g
                #print "updated granularity", granularity
            elif candles > 300: break
        print "Found new optimal granularity: ", granularity, " resulting in ", str(int(timeRange / granularity)), " candles"

    #Convert datetime objects to strings
    end = end.isoformat()
    start = start.isoformat()

    #Defind json data payload
    trend = {
        'start' : start,
        'end' : end,
        'granularity' : granularity
    }

    #Define url, execute GET request
    trend_url = api_url + '/products/' + product_id + '/candles'
    response = requests.get(trend_url, trend)

    if response.status_code is not 200:
        raise Exception('Invalid GDAX Status Code: %d' % response.status_code)
    elif len(response.json()) == 0:
        raise Exception('GDAX return status code 200, but the response was empty!')

    return response
#==============================================================================    
def updateAll(product_id, timeframe, dataStruct, api_url):
    #NOTE: 'dataStruct' is a dictionary as shown below:
    '''
    {
    "data"             : deque(), \
    "lowMean"          : 0,       \
    "lowestLow"        : 999999,  \
    "lowSumOfSquares"  : 0,       \
    "lowStdDev"        : 0,       \
    "highMean"         : 0,       \
    "highestHigh"      :-999999,  \
    "highSumOfSquares" : 0,       \
    "highStdDev"       : 0,       \
    "openMean"         : 0,       \
    "openSumOfSquares" : 0,       \
    "openStdDev"       : 0,       \
    "closeMean"        : 0,       \
    "closeSumOfSquares": 0,       \
    "closeStdDev"      : 0  }
    '''

    global gProductIDs, gTimeframes, gTimeframeToHourDelta, gFieldToIndex
    records = []

    #Error checking
    if product_id not in gProductIDs: 
        print "Error in updateAll(): product_id argument", product_id + "is not a valid product_id!"
        return -1

    if timeframe not in gTimeframeToGranularity:
        print "Error in updateAll(): timeframe argument", timeframe + "is not a valid timeframe!"
        return -2

    granularity = gTimeframeToGranularity[timeframe]
    currentTime = requests.get(api_url + '/time')
    end = datetime.utcfromtimestamp(currentTime.json()['epoch'])
    #print "The current time is:", end
    #print "The current time in epoch is:",currentTime.json()['epoch']
    r = ''

    #First, check if the "data" deque is empty, if so, we need to initalize it for the first time
    if not dataStruct["data"]:
        start = end - timedelta(hours=gTimeframeToHourDelta[timeframe])    
        #r = getHistoricRate(api_url, product_id, start, end, granularity)

        #30d trend require 3 http requests
        if timeframe == '30d':
            now = end
            for i in range(0,30,10):
                #end = now + timedelta(days=i)
                #start = now + timedelta(days=(i-10))
                end = now - timedelta(days=i)
                start = now - timedelta(days=(i+10))           
                #print "i is: ", i
                #print "30d request:"
                #print "START: ",start
                #print "END:   ",end   

                r = getHistoricRate(api_url, product_id, start, end, granularity)

                if r.status_code < 200 or r.status_code >= 300:
                    print "Error getting 30 day trend, HTTP response code is: ", str(r.status_code)
                    print "Response text is:", r.text
                    return -3 

                else:
                    records = r.json()[:240]
                    for record in records:
                        #Note that in this block any comment regarding "update the ...mean" simply indicates 
                        #that I will create a rolling sum.  The division will happen later once all values are summed.

                        #Update the lowestLow
                        if record[gFieldToIndex["low"]] < dataStruct["lowestLow"]:
                            dataStruct["lowestLow"] = record[gFieldToIndex["low"]]
                        #Update the lowMean     (lM)
                        dataStruct["lowMean"] += record[gFieldToIndex["low"]]

                        #Update the highestHigh
                        if record[gFieldToIndex["high"]] > dataStruct["highestHigh"]:
                            dataStruct["highestHigh"] = record[gFieldToIndex["high"]]
                        #Update the highMean    (hM)
                        dataStruct["highMean"] += record[gFieldToIndex["high"]]

                        #Update the openMean    (oM)
                        dataStruct["openMean"] += record[gFieldToIndex["open"]]

                        #Update the closeMean   (cM)
                        dataStruct["closeMean"] += record[gFieldToIndex["close"]]

                        dataStruct["data"].appendleft(record)
                    #btc_30d_trend.appendleft("======================================")
                time.sleep(2)

        #1hr, 1d, and 7d trends can all be handled with this code
        else:

            start = end - timedelta(hours=gTimeframeToHourDelta[timeframe])  
            #print "start:", start
            #print "end  :", end
            #print timeframe
            #Sprint "granularity:", granularity  
            r = getHistoricRate(api_url, product_id, start, end, granularity) 
            if r.status_code < 200 or r.status_code >= 300:
                print "Error getting ", timeframe, " trend, HTTP response code is: ", str(r.status_code)
                print "Response text is:", r.text
                return -4
            else: 
                #Note that GDAX returns 300 results by defaults, so grab the first N results 
               if timeframe == "1hr":
                   records = r.json()[:60]
               elif timeframe == "1d":
                   records = r.json()[:288]
               elif timeframe == "7d":
                   records = r.json()[:168]
               elif timeframe == "30d":
                   records = r.json()[:240]
                    
               for record in records:
                    #Update the lowestLow
                    if record[gFieldToIndex["low"]] < dataStruct["lowestLow"]:
                        dataStruct["lowestLow"] = record[gFieldToIndex["low"]]
                    #Update the highestHigh
                    if record[gFieldToIndex["high"]] > dataStruct["highestHigh"]:
                        dataStruct["highestHigh"] = record[gFieldToIndex["high"]]

                    dataStruct["lowMean"] += record[gFieldToIndex["low"]]
                    dataStruct["highMean"] += record[gFieldToIndex["high"]]
                    dataStruct["openMean"] += record[gFieldToIndex["open"]]
                    dataStruct["closeMean"] += record[gFieldToIndex["close"]]

                    #print "Datapoint:",record
                    #btc_1hr_trend[datapoint[0]] = datapoint[1:]
                    dataStruct["data"].appendleft(record)
            #for item in dataStruct["data"]:
            #    print item
            #print "type(r.json): " , type(r.json())

        
        #Finish calcuating the mean - divide by N
        dequeLength = len(dataStruct["data"])
        #print dequeLength
        dataStruct["lowMean"]   /= dequeLength
        dataStruct["highMean"]  /= dequeLength
        dataStruct["openMean"]  /= dequeLength
        dataStruct["closeMean"] /= dequeLength

        #Now find the StdDev
        for record in dataStruct["data"]:
            #Update the Variances 
            dataStruct["lowVariance"] += (record[gFieldToIndex["low"]] -  dataStruct["lowMean"]) ** 2        
            dataStruct["highVariance"] += (record[gFieldToIndex["high"]] - dataStruct["highMean"]) ** 2
            dataStruct["openVariance"] += (record[gFieldToIndex["open"]] - dataStruct["openMean"]) ** 2
            dataStruct["closeVariance"] += (record[gFieldToIndex["close"]] - dataStruct["closeMean"]) ** 2

        dataStruct["lowVariance"]   /= dequeLength
        dataStruct["highVariance"]  /= dequeLength
        dataStruct["openVariance"]  /= dequeLength
        dataStruct["closeVariance"] /= dequeLength

        dataStruct["lowStdDev"]   = math.sqrt( dataStruct["lowVariance"] )
        dataStruct["highStdDev"]  = math.sqrt( dataStruct["highVariance"] )
        dataStruct["openStdDev"]  = math.sqrt( dataStruct["openVariance"]  )
        dataStruct["closeStdDev"] = math.sqrt( dataStruct["closeVariance"] )

        return dataStruct

    #The deque exists, so we're simply updating it - Note that GDAX returns 300 records by default,
    #So we need to slice the desired records out of the 300 returned results.
    else:
        #Peek at the last item in the deque; note that the first item will be the UTC epoch 
        start =  dataStruct["data"][-1][0]
        #currentTime = requests.get(api_url + '/time')
        #now = currentTime.json()['epoch']
        currentTime = requests.get(api_url + '/time')
        end = datetime.utcfromtimestamp(currentTime.json()['epoch'])
        end = currentTime.json()['epoch']
        #print "Current Epoch time:", end
        #print "Epoch time of last:", start
        diff = end - start
        #print "Difference:", diff
        update = int(diff / granularity)
        #print "Difference / " ,granularity, ":", update
        
        #print "End is   :", end
        #print "Start is :", start 
        
        if update == 0:
            print "Nothing to update."
            return dataStruct

        print "Updating ", update, "records"
        #'update' now holds the number of <granularity units> since the last update, so we need to pop
        #that # of elements from the left of the deque and push the same # of new elements 
        #to the right side - updating the mean and std. dev. as we do so 
        if update > 300:   
            #TODO Rather than throw an error here, reset 'dataStruct' to the default values, call 
            #this functions recursively with the default data structure, and immediately return 
            #the result.  In essence, simply create the data struct as if for the first time, b/c
            #a good chunk of the data needed to be discarded and repopulated anyway.
            print "Error: Attempting to update deque, but 'update' is > 300!" 
            return

        start = datetime.utcfromtimestamp(start)
        end   = datetime.utcfromtimestamp(end)

        #print "type(r):", type(r)
        #print "r:", r
        #print "api:", api_url, "\npid: ", product_id, "\nstart:" ,start, "\nend :",end, "\ngranularity:",granularity
        r = getHistoricRate(api_url, product_id, start, end, granularity)
        #print "type(r):", type(r)
        #print "r:", r
        if r.status_code < 200 or r.status_code >= 300:
            print "Error getting ", timeframe, " trend, HTTP response code is: ", str(r.status_code)
            print "Response text is:", r.text
            return -5      
        
        #Note the slicing to reverse the list: e.g.
        #Current time: 10
        #Current data: 1,2,3,4,5,6,7
        #r: 10,9,8
        #print "Updating a dataStruct: r.json() is of type:", type(r.json())
        #print "r.json() is:", r.json()

        records = r.json()[:update]
        #print "records len() is", len(records)
        #print "About to update from the following list:"
        #for r in records:
        #    print r

        dequeLength = len(dataStruct["data"])
        for newRecord in records[::-1]:
            #Update the deque of data
            oldRecord = dataStruct["data"].popleft()
            dataStruct["data"].append(newRecord)

            #print "pop :", oldRecord
            #print "push:", newRecord

            lowMean = dataStruct["lowMean"]  
            highMean = dataStruct["highMean"] 
            openMean = dataStruct["openMean"] 
            closeMean = dataStruct["closeMean"] 

            #Now re-calculate all the statistics

            #Recalculate the means (averages)
            dataStruct["lowMean"] += ((newRecord[gFieldToIndex["low"]] - oldRecord[gFieldToIndex["low"]]) / dequeLength)
            dataStruct["highMean"] += ((newRecord[gFieldToIndex["high"]] - oldRecord[gFieldToIndex["high"]]) / dequeLength)
            dataStruct["openMean"] += ((newRecord[gFieldToIndex["open"]] - oldRecord[gFieldToIndex["open"]]) / dequeLength)
            dataStruct["closeMean"] += ((newRecord[gFieldToIndex["close"]] - oldRecord[gFieldToIndex["close"]]) / dequeLength)

            #Recalculate the variance based on this formula: http://jonisalonen.com/2014/efficient-and-accurate-rolling-standard-deviation/
            dataStruct["lowVariance"] += (newRecord[gFieldToIndex["low"]] - oldRecord[gFieldToIndex["low"]])* \
                (newRecord[gFieldToIndex["low"]]-dataStruct["lowMean"]+oldRecord[gFieldToIndex["low"]]-lowMean)/dequeLength
            dataStruct["highVariance"] += (newRecord[gFieldToIndex["high"]] - oldRecord[gFieldToIndex["high"]])* \
                (newRecord[gFieldToIndex["high"]]-dataStruct["highMean"]+oldRecord[gFieldToIndex["high"]]-highMean)/dequeLength
            dataStruct["openVariance"] += (newRecord[gFieldToIndex["open"]] - oldRecord[gFieldToIndex["open"]])* \
                (newRecord[gFieldToIndex["open"]]-dataStruct["openMean"]+oldRecord[gFieldToIndex["open"]]-openMean)/dequeLength
            dataStruct["closeVariance"] += (newRecord[gFieldToIndex["close"]] - oldRecord[gFieldToIndex["close"]])* \
                (newRecord[gFieldToIndex["close"]]-dataStruct["closeMean"]+oldRecord[gFieldToIndex["close"]]-closeMean)/dequeLength


            #Now Recalculate the stddev by simply taking the sqrt of the variance
            dataStruct["lowStdDev"]   = math.sqrt( dataStruct["lowVariance"])
            dataStruct["highStdDev"]  = math.sqrt( dataStruct["highVariance"])
            dataStruct["openStdDev"]  = math.sqrt( dataStruct["openVariance"])
            dataStruct["closeStdDev"] = math.sqrt( dataStruct["closeVariance"])

        return dataStruct
#==============================================================================
def main(argv):
    #TODO
    '''Spawn 2 threads: one to handle user interaction and another to 
    interact with the exchange, store the data, calculate stats, etc
    The user thread should be able to give info to the user e.g.:
    1. "Thread 2 is sleeping for N seconds"
    2. "Current price is N standard deviations -/+ the <timeframe> mean
    3. "Thread 2 is in a 'soft-buy' state, etc.
    4. "Press 'q' to kill the process.
    5. "type 'bg' to background this process"
    etc.
        
    '''
    api_url = 'https://api.gdax.com/'
    currentTime = requests.get(api_url + '/time')
    now = datetime.utcfromtimestamp(currentTime.json()['epoch'])
    #print currentTime.json()
    #print now
    #sys.exit(1)

    #Enable access to the global stop flag 
    global gStopFlag

    #Register signal handler to catch interrupts
    signal.signal(signal.SIGINT, signal_handler)

    #Declare and initalize GDAX authentication variables
    #api_url = 'https://api.gdax.com/'
    #Use the sandbox for testing
    #TODO Enter your own creds here
    api_url = 'https://api-public.sandbox.gdax.com'
    api_key = 'MYAPIKEYHERE'
    api_secret = 'MYAPISECERETHERE'
    passphrase = 'MYPASSPHRASEHERE'
    auth = CoinbaseExchangeAuth(api_key, api_secret, passphrase)

    #Wake once per hour by default, though this value will change dynamically based on the state (see below)
    state_intervals= {\
        #Update every 05 minutes when poised to execute sell order        
        "strong_sell": 300,  \
        #Update every 15 minutes when prices are rising   
        "soft_sell":   900, \
        #Update once an hour when prices are stable
        "hold":        60, \
        #"hold":        3600, \
        #Update every 15 minutes when prices are falling
        "soft_buy":    900, \
        #Update every 05 minutes when poised to execute buy order
        "strong_buy":  300   \
        }

    #Create field headers in the csv log files if they don't yet exist
    if not os.path.isfile("transaction1.csv"):
       with open("transaction1.csv", "a") as file:
         file.write("Time,Coin,30d Z score,7d Z-score,1d Z-score,Mkt Decision\n")
    if not os.path.isfile("transaction2.csv"):
       with open("transaction2.csv", "a") as file:
          file.write("Time,Coin,30d Z score,7d Z-score,1d Z-score,Mkt Decision\n")

    cryptos = ["BTC-USD"]#,"LTC-USD"]
    timeFrames = [ "1d", "7d", "30d"] #"1hr",

    #Define dictionaries to hold trend data for each crypto - for now, let's just do BTC
    #Note that we can only retrieve 300 records per request
    #Historical data is returned as [ time, low, high, open, clocse, volume ]
    #btc_1hr_trend = deque()   #60 records, 1 per minute         #   300 * 60 s = 5 hr
    #btc_1d_trend  = deque()   #288 recores, 1 per 5 minutes     #   300 * 300s =  25 hrs
    #btc_7d_trend  = deque()   #168 records, 1 per hour          #   300 * 3600 = 12.5 D
    #btc_30d_trend = deque()   #720 records, 1 per hour
    #            Total: 1,236 records | max ~ 68 bytes/record    
    #            Total space: 1,236*68 = 84,048 = 82kB

    #Initalize the data structs holding the stats for each coin
    cryptoData = {}
    cryptoState = {}
    cryptoZScores = {}
    for crypto in cryptos:
        cryptoData[crypto] = {}
        cryptoState[crypto] = "hold"
        cryptoZScores[crypto] = {}
        for timeFrame in timeFrames:
            cryptoZScores[crypto][timeFrame] = 0
            cryptoData[crypto][timeFrame] = {
            "data"             : deque(), \
            "lowMean"          : 0,       \
            "lowestLow"        : 999999,  \
            "lowVariance"      : 0,       \
            "lowStdDev"        : 0,       \
            "highMean"         : 0,       \
            "highestHigh"      :-999999,  \
            "highVariance"     : 0,       \
            "highStdDev"       : 0,       \
            "openMean"         : 0,       \
            "openVariance"     : 0,       \
            "openStdDev"       : 0,       \
            "closeMean"        : 0,       \
            "closeVariance"    : 0,       \
            "closeStdDev"      : 0  }

    #Time variables for trend data
    start = ''
    end = ''
    
    api_url = 'https://api.gdax.com/'
       
    #TODO Spawn one thread per crypto - use a mutex to limit request rate
    #Core logic loop 
    while not gStopFlag:

        #For each crypto/coin I'm tracking:
        for crypto, cryptoDict in cryptoData.iteritems():
            if gStopFlag: break
            #print "crypto:", crypto
            for timeframe in cryptoDict:
                if gStopFlag: break
                #print timeframe,cryptoDict[timeframe]
                #Iterate over each time frame for which I'm tracking it:
                #print "-----------------------------------------------------------------------------"
                print "Updating:", crypto, timeframe
                #print 
                cryptoDict[timeframe] = updateAll(crypto, timeframe, cryptoDict[timeframe], api_url)
                time.sleep(1)
                currentPrice = requests.get(api_url + 'products/'+crypto+'/ticker')
                if currentPrice.status_code >= 200 and currentPrice.status_code < 300:
                    print "Current Price:", currentPrice.json()["price"]
                else:
                    print "Error getting current price"
                '''
                print "Time Frame:", timeframe, "lowestLow:   ", cryptoDict[timeframe]["lowestLow"]
                print "Time Frame:", timeframe, "lowMean:     ", cryptoDict[timeframe]["lowMean"]
                print "Time Frame:", timeframe, "lowStdDev:   ", cryptoDict[timeframe]["lowStdDev"]
                print "Time Frame:", timeframe, "highestHigh: ", cryptoDict[timeframe]["highestHigh"]
                print "Time Frame:", timeframe, "highMean:    ", cryptoDict[timeframe]["highMean"]
                print "Time Frame:", timeframe, "highStdDev:  ", cryptoDict[timeframe]["highStdDev"]
                print "Time Frame:", timeframe, "openMean:    ", cryptoDict[timeframe]["openMean"]
                print "Time Frame:", timeframe, "openStdDev:  ", cryptoDict[timeframe]["openStdDev"]
                print "Time Frame:", timeframe, "closeMean:   ", cryptoDict[timeframe]["closeMean"]
                print "Time Frame:", timeframe, "closeStdDev: ", cryptoDict[timeframe]["closeStdDev"]
                print ""
                '''
                #print "Now the current price in terms of Z-scores:"
              
                lowZScore  = (float(currentPrice.json()["price"]) - cryptoDict[timeframe]["lowMean"] )   / cryptoDict[timeframe]["lowStdDev"]
                highZScore = (float(currentPrice.json()["price"]) - cryptoDict[timeframe]["highMean"] )  / cryptoDict[timeframe]["highStdDev"]
                openZScore = (float(currentPrice.json()["price"]) - cryptoDict[timeframe]["openMean"] )  / cryptoDict[timeframe]["openStdDev"]
                closeZScore= (float(currentPrice.json()["price"]) - cryptoDict[timeframe]["closeMean"] ) / cryptoDict[timeframe]["closeStdDev"]                  
                  
                cryptoZScores[crypto][timeframe] = float(lowZScore + highZScore +  openZScore + closeZScore ) / 4.0

                print "Average Z score:", cryptoZScores[crypto][timeframe]
                print "-----------------------------------------------------------------------------"
                '''
                print "lowestZScore: ",  str(lowZScore)
                print "highestZScore:", str(highZScore)
                print "openZScore:   ",    str(openZScore)
                print "closeZScore:  ",   str(closeZScore)

                
                if timeframe == "30d":
                    if lowZScore < -2.9: state = 'strong_buy'
                    elif lowZScore < -1.9: state = 'soft_buy'
                    elif abs(lowZScore) < 1: state = 'hold'
                    elif lowZScore > -1.9: state = 'soft_sell'
                    else: state = 'strong_sell'
                '''  
                    
                time.sleep(5)


        currentTime = requests.get(api_url + '/time')
        now = datetime.utcfromtimestamp(currentTime.json()['epoch'])

        #For each crypto/coin I'm tracking, check the Z-scores for various timeframes to make a market decision
        #based on the MarketDecision spreadsheet on the desktop - LogicMatrix 1
        for crypto, cryptoDict in cryptoData.iteritems():
           if gStopFlag: break
           #print "crypto:", crypto
           if (cryptoData[crypto]["30d"] <= -1) and (cryptoData[crypto]["7d"] <= -2) and (cryptoData[crypto]["1d"] > 1): 
              cryptoState[crypto] = "buy"
           elif (cryptoData[crypto]["30d"] >= 1) and (cryptoData[crypto]["7d"] >= 2) and (cryptoData[crypto]["1d"] < 1): 
                    cryptoState[crypto] = "sell"
           else: cryptoState[crypto] = "hold"



           print "Logic Matrix #1: Status for ", crypto, " is ", cryptoState[crypto]
           #if cryptoState[crypto] != "hold":
           with open("transaction1.csv", "a") as file:
              file.write(str(now) + "," + crypto + "," + \
                        currentPrice.json()["price"]  + \
                        str(cryptoZScores[crypto]["30d"]) + "," + \
                        str(cryptoZScores[crypto]["7d"]) + ","  + \
                        str(cryptoZScores[crypto]["1d"]) + ","  + \
                        cryptoState[crypto] + "\n")


        #For each crypto/coin I'm tracking, check the Z-scores for various timeframes to make a market decision
        #based on the MarketDecision spreadsheet on the desktop - Logic Matrix 2
        for crypto, cryptoDict in cryptoData.iteritems():
           if gStopFlag: break
           #print "crypto:", crypto
           if (cryptoData[crypto]["7d"] <= -2) and (cryptoData[crypto]["1d"] > 1): 
              cryptoState[crypto] = "buy"
           elif (cryptoData[crypto]["7d"] >= 2) and (cryptoData[crypto]["1d"] < 1): 
                    cryptoState[crypto] = "sell"
           else: cryptoState[crypto] = "hold"

           print "Logic Matrix #2: Status for ", crypto, " is ", cryptoState[crypto]
           #if cryptoState[crypto] != "hold":
           with open("transaction2.csv", "a") as file:
              file.write(str(now) + "," + crypto + "," + \
                        str(cryptoZScores[crypto]["30d"]) + "," + \
                        str(cryptoZScores[crypto]["7d"]) + ","  + \
                        str(cryptoZScores[crypto]["1d"]) + ","  + \
                        cryptoState[crypto] + "\n")
                


        if gStopFlag:
            #TODO Clean up here 
            print "in main(), exiting due to interrupt"
            sys.exit(1)

        sleeptime = 300
        print "Sleeping for", sleeptime, " seconds."
        time.sleep(sleeptime)
        print "-----------------------------------------------------------------------------"
        #Sleep for some period of time as determined by the current state
        #print "Sleeping for", state_intervals[cryptoState[crypto]]," seconds."
        #time.sleep(state_intervals[cryptoState[crypto]])


    # Get accounts
    #r = requests.get(api_url + '/accounts', auth=auth)
    #print r.json()
    # [{"id": "a1b2c3d4", "balance":...

    # Place an order - limit is the default type
    order = {
        'size': .001,
        'price': .001,
        'side': 'buy',
        'product_id': 'BTC-USD',
    }

    #r = requests.post(api_url + '/orders', json=order, auth=auth)
    #print r.json()
   
    #r = requests.get(order_url, auth=auth)
    #print r.json()["status"]

    if gStopFlag:
        #TODO Clean up here, e.g. write out trend data to a file
        print "in main(), exiting due to interrupt"
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv)






