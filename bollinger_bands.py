from turtle import width
import pandas as pd
import time
import multiprocessing as mp
import matplotlib 
import numpy as np

# local imports
from backtester import engine, tester
from backtester import API_Interface as api


bt = [10,20,50]
stdv = [1.5,2,2.5]
standard_deviations = 3.5
buyvariablescale = 1
stop_standard_deviation = 0.5
training_period = 20

'''
logic() function:
    Context: Called for every row in the input data.

    Input:  account - the account object
            lookback - the lookback dataframe, containing all data up until this point in time

    Output: none, but the account object will be modified on each call
'''

def logic(account, lookback): # Logic function to be used for each time interval in backtest 
    today = len(lookback)-1

    for i in [0,1,2]:
        buyvariable = buyvariablescale*standard_deviations
        buylongamount = account.buying_power*(1-buyvariable/((lookback["BOLD"+str(i)][today]-lookback['close'][today])+buyvariable))
        buyshortamount = account.buying_power*(1-buyvariable/((lookback['close'][today]-lookback["BOLU"+str(i)][today])+buyvariable))

        if(today > bt[i]): # If the lookback is long enough to calculate the Bollinger Bands

            if(lookback['close'][today] < lookback["BOLD"+str(i)][today]): # If current price is below lower Bollinger Band, enter a long position
                '''for position in account.positions: # Close all current positions
                    account.close_position(position, 1, lookback['close'][today])'''
                if(account.buying_power > 0):
                    account.enter_position('long', account.buying_power, lookback['close'][today])
                    #account.enter_position('long', buylongamount, lookback['close'][today]) # Enter a long position

            if(lookback['close'][today] > lookback["BOLU"+str(i)][today]): # If today's price is above the upper Bollinger Band, enter a short position
                if(account.buying_power > 0):
                    account.enter_position('short', account.buying_power, lookback['close'][today])
                    #account.enter_position('short', buyshortamount, lookback['close'][today]) # Enter a short position
        
    if (lookback['close'][today] < lookback['MA-TP0'][today]+lookback['std0'][today]*stop_standard_deviation and lookback['close'][today] > lookback['MA-TP0'][today]-lookback['std0'][today]*stop_standard_deviation):
        for position in account.positions: # Close all current positions
            account.close_position(position, 1, lookback['close'][today])

'''
preprocess_data() function:
    Context: Called once at the beginning of the backtest. TOTALLY OPTIONAL. 
             Each of these can be calculated at each time interval, however this is likely slower.

    Input:  list_of_stocks - a list of stock data csvs to be processed

    Output: list_of_stocks_processed - a list of processed stock data csvs
'''
def preprocess_data(list_of_stocks):
    list_of_stocks_processed = []
    for stock in list_of_stocks:
        df = pd.read_csv("data/" + stock + ".csv", parse_dates=[0])
        df['TP'] = (df['close'] + df['low'] + df['high'])/3 # Calculate Typical Price
        
        for i in [0,1,2]:
            df['std'+str(i)] = df['TP'].rolling(bt[i]).std() # Calculate Standard Deviation
            df['MA-TP'+str(i)] = df['TP'].rolling(bt[i]).mean() # Calculate Moving Average of Typical Price
            df['BOLU'+str(i)] = df['MA-TP'+str(i)] + stdv[i]*df['std'+str(i)] # Calculate Long Upper Bollinger Band
            df['BOLD'+str(i)] = df['MA-TP'+str(i)] - stdv[i]*df['std'+str(i)] # Calculate Long Lower Bollinger Band

        df.to_csv("data/" + stock + "_Processed.csv", index=False) # Save to CSV
        list_of_stocks_processed.append(stock + "_Processed")
    return list_of_stocks_processed

if __name__ == "__main__":
    # list_of_stocks = ["TSLA_2020-03-01_2022-01-20_1min"] 
    list_of_stocks = ["TSLA_2020-03-09_2022-01-28_15min", "AAPL_2020-03-24_2022-02-12_15min"] # List of stock data csv's to be tested, located in "data/" folder 
    list_of_stocks_proccessed = preprocess_data(list_of_stocks) # Preprocess the data
    results = tester.test_array(list_of_stocks_proccessed, logic, chart=False) # Run backtest on list of stocks using the logic function

    #print("training period " + str(training_period))
    #print("standard deviations " + str(standard_deviations))
    df = pd.DataFrame(list(results), columns=["Buy and Hold","Strategy","Longs","Sells","Shorts","Covers","Stdev_Strategy","Stdev_Hold","Stock"]) # Create dataframe of results
    df.to_csv("results/Test_Results.csv", index=False) # Save results to csv