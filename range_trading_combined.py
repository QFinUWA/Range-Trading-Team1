import pandas as pd
import time
import multiprocessing as mp
import average_true_range

# local imports
from backtester import engine, tester
from backtester import API_Interface as api

training_period = 20 # How far the rolling average and ADX take into calculation
standard_deviations = 3.5 # Number of Standard Deviations from the mean the Bollinger Bands sit
bound_buffer = 1 # How many SDs above/below the min/max of a given time period the ranges sit
enter_position_std = 0.05 # How many SDs above/below the range bounds buy and sell signals are given at
stop_loss = 1 # How many SDs above/below the range is considered a breakout and will cause all positions to be exited
adx_ranging_threshold = 25 # ADX value below which market is considered to be ranging

range_start = -1 # Global variable (not a parameter!!!) for the starting position of a range

'''
identify_range() function:
    Context: Called when the market has been identified to be sideways (the starting point of
    which is passed as a parameter to the function). Will identify the range within which the
    market is operating and other related parameters.

    Input:  lookback - the lookback dataframe, containing all data up until this point in time
            start - the date at which the market began drifting sideways

    Output: a tuple of values representing the lower and upper bound, respectively
'''
def identify_range(lookback, start):
    lower = min(lookback['close'][start:]) - bound_buffer*standard_deviations(lookback['close'][start:])
    upper = max(lookback['close'][start:]) + bound_buffer*standard_deviations(lookback['close'][start:])
    buy_signal = lower + enter_position_std*standard_deviations(lookback['close'][start:])
    sell_signal = upper - enter_position_std*standard_deviations(lookback['close'][start:])
    stop_loss_lower = lower - stop_loss*standard_deviations(lookback['close'][start:])
    stop_loss_upper = upper + stop_loss*standard_deviations(lookback['close'][start:])

    return (lower, upper, buy_signal, sell_signal, stop_loss_lower, stop_loss_upper)

'''
exit_positions() function:
    Context: Called to liquidate all positions currently held.

    Input: account - the account object upon which to act

    Output: void
'''
def exit_positions(account, lookback, today):
    for position in account.positions:
        account.close_position(position, 1, lookback['close'][today])

'''
mean() function:
    Context: returns the mean of a set of data

    Input: data

    Ouptut: the mean
'''
def mean(data):
    return sum(data)/len(data)

'''
adx() function:
    Context: returns a number between 0 and 100 representing the average directional index (ADX) of the data at the most recent date.

    Input: lookback - the data, up to the current date

    Output: integer between 0 and 100
'''
def adx(lookback):
    today = len(lookback) - 1
    if len(lookback) < 2*training_period + 1:
        return 100

    dx_array = []

    for i in range(training_period):
        ATR = lookback['ATR'][today-i]

        smoothed_plusDM = mean([lookback['high'][today-i-x]-lookback['high'][today-i-1-x] for x in range(training_period)])
        smoothed_minusDM = mean([lookback['low'][today-i-1-x]-lookback['low'][today-i-x] for x in range(training_period)])

        plusDI = (smoothed_plusDM / ATR)*100
        minusDI = (smoothed_minusDM / ATR)*100
        DX = (abs(plusDI - minusDI)/abs(plusDI + minusDI))*100
        dx_array.append(DX)

    ADX = sum(dx_array) / training_period
    return ADX

'''
logic() function:
    Context: Called for every row in the input data.

    Input:  account - the account object
            lookback - the lookback dataframe, containing all data up until this point in time

    Output: none, but the account object will be modified on each call
'''
def logic(account, lookback): # Logic function to be used for each time interval in backtest 
    today = len(lookback)-1

    if today + 1 < 2*training_period + 1: # make sure there is enough data for calculations to work
        return

    ranging = adx(lookback) < adx_ranging_threshold
    global range_start

    if range_start == -1 and ranging:
        range_start = today
    elif range_start != -1 and not ranging:
        exit_positions(account)
        range_start = -1

    if ranging:
        lower, upper, buy_signal, sell_signal, stop_loss_lower, stop_loss_upper = identify_range(lookback, range_start)
        price = lookback['close'][today]

        if price <= stop_loss_lower or price >= stop_loss_upper:
            exit_positions(account, lookback, today)
        elif price <= buy_signal:
            exit_positions(account, lookback, today)
            account.enter_position('long', account.buying_power, price)
        elif price >= sell_signal:
            exit_positions(account, lookback, today)
            account.enter_position('short', account.buying_power, price)
    else:
        range_start = -1

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
        df.to_csv("data/" + stock + "_Processed.csv", index=False) # Save to CSV
        list_of_stocks_processed.append(stock + "_Processed")
    return list_of_stocks_processed

if __name__ == "__main__":
    # list_of_stocks = ["TSLA_2020-03-01_2022-01-20_1min"] 
    list_of_stocks = ["TSLA_2020-03-09_2022-01-28_15min", "AAPL_2020-03-24_2022-02-12_15min"] # List of stock data csv's to be tested, located in "data/" folder 
    list_of_stocks_proccessed = average_true_range.preprocess_data(list_of_stocks) # Preprocess the data
    results = tester.test_array(list_of_stocks_proccessed, logic, chart=True) # Run backtest on list of stocks using the logic function

    print("training period " + str(training_period))
    print("standard deviations " + str(standard_deviations))
    df = pd.DataFrame(list(results), columns=["Buy and Hold","Strategy","Longs","Sells","Shorts","Covers","Stdev_Strategy","Stdev_Hold","Stock"]) # Create dataframe of results
    df.to_csv("results/Test_Results.csv", index=False) # Save results to csv
