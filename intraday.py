import pandas as pd
import yfinance as yf
import numpy as np

def get_stock_data(ticker, period='1d', interval='1m'):
    # Fetch historical stock data
    stock_data = yf.download(ticker, period=period, interval=interval)
    return stock_data

def calculate_sma(data, window):
    # Calculate Simple Moving Average
    sma = data['Close'].rolling(window=window).mean()
    return sma

def generate_signals(data, short_window=50, long_window=200):
    # Generate signals based on SMA crossover
    signals = pd.DataFrame(index=data.index)
    signals['price'] = data['Close']
    signals['short_sma'] = calculate_sma(data, short_window)
    signals['long_sma'] = calculate_sma(data, long_window)
    signals['signal'] = 0.0
    signals['signal'][short_window:] = np.where(
        signals['short_sma'][short_window:] > signals['long_sma'][short_window:], 1.0, 0.0
    )
    signals['positions'] = signals['signal'].diff()
    return signals

def simulate_trading(signals, initial_capital=100000.0):
    # Simulate trading based on signals
    positions = pd.DataFrame(index=signals.index).fillna(0.0)
    positions['stock'] = 100 * signals['signal']  # Number of shares
    portfolio = positions.multiply(signals['price'], axis=0)
    pos_diff = positions.diff()
    
    portfolio['holdings'] = positions.multiply(signals['price'], axis=0).sum(axis=1)
    portfolio['cash'] = initial_capital - (pos_diff.multiply(signals['price'], axis=0).sum(axis=1).cumsum())
    portfolio['total'] = portfolio['cash'] + portfolio['holdings']
    portfolio['returns'] = portfolio['total'].pct_change()
    return portfolio

def main():
    ticker = 'AAPL'
    data = get_stock_data(ticker)
    
    short_window = 50
    long_window = 200
    
    signals = generate_signals(data, short_window, long_window)
    portfolio = simulate_trading(signals)
    
    print(portfolio)

if __name__ == "__main__":
    main()