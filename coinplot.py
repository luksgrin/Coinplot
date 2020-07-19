import requests, datetime, time, plotly
import numpy as np
import pandas as pd
import plotly.graph_objs as go
from plotly.subplots import make_subplots

def rsiFunc(prices, n=14):

    prices  = prices.to_numpy()
    deltas  = np.diff(prices)
    seed    = deltas[:n + 1]
    up      = seed[seed >= 0].sum()/n
    down    = - seed[seed < 0].sum()/n
    rs      = up/down
    rsi     = np.zeros_like(prices)
    rsi[:n] = 100.0 - 100.0/(1.0 + rs)

    for i in range(n, len(prices)):
        delta = deltas[i - 1] # becacause the diff is 1 shorter

        if delta > 0:
            upval   = delta
            downval = 0.0
        else:
            upval   = 0.0
            downval = - delta

        up     = (up*(n - 1) + upval)/n
        down   = (down*(n - 1) + downval)/n

        rs     = up/down
        rsi[i] = 100.0 - 100.0/(1.0 + rs)

    return rsi

def movingaverage(values, window):

    values = values.to_numpy()
    weigths = np.repeat(1.0, window)/window
    smas    = np.convolve(values, weigths, 'valid')

    return smas # as a numpy array

def ExpMovingAverage(values, window):

    values = values.to_numpy()
    weights    = np.exp(np.linspace(-1.0, 0.0, window))
    weights   /= weights.sum()
    a          =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]

    return a

def computeMACD(x, slow=26, fast=12):

    """
    compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    return value is emaslow, emafast, macd which are len(x) arrays
    """

    emaslow = ExpMovingAverage(x, slow)
    emafast = ExpMovingAverage(x, fast)

    return emaslow, emafast, emafast - emaslow

def pair_slopes(x): # La pendiente entre dos puntos de la diferencia de MACD

    x = x.to_numpy()
    x = (x[1:] - x[:-1])
    x = np.append(np.zeros(1), x)

    return x


def retrieve_data(
                  start=(datetime.datetime.now() - datetime.timedelta(hours=5)).isoformat(),
                  end=datetime.datetime.now().isoformat(),
                  gran=60
                  ) -> {
                        'start': 'Starting time window (in ISO 8601)', # Ejemplo ISO format: '2020-04-07T15:51:23.488999'
                        'end'  : 'Ending time window (in ISO 8601)',
                        'gran' : 'Desired timeslice for candles. Must be one of the following values: {60, 300, 900, 3600, 21600, 86400}'
                        }:

    COINBASE_URL = 'https://api.pro.coinbase.com'

    Params = {
              'start'       : start,
              'end'         : end,
              'granularity' : gran
              }

    # Lista con las velas
    response = requests.get(COINBASE_URL + '/products/BTC-EUR/candles/', params=Params).json()
    N = np.array(response)

    # Data frame con los datos de las velas
    df = pd.DataFrame(
                      {'close'    : N[:, 4],
                       'high'     : N[:, 2],
                       'low'      : N[:, 1],
                       'open'     : N[:, 3],
                       'volume'   : N[:, 5],
                       'datetime' : N[:, 0]
                       }
                      )

    df['datetime'] = df['datetime'].apply(
                                          lambda t : time.strftime(
                                                                   '%Y-%m-%d %H:%M:%S',
                                                                   time.localtime(t)
                                                                   )
                                          )
    return df

def main():

    df = retrieve_data()

    df['MACDAS_diff']   = computeMACD(df['close'])[-1]
    df['MACDAS_slopes'] = pair_slopes(df['MACDAS_diff'])

    df.to_csv('Candle_df.csv')

    CNDSTCK = go.Candlestick(
                             x          = df['datetime'],
                             open       = df['open'],
                             high       = df['high'],
                             low        = df['low'],
                             close      = df['close'],
                             showlegend=False,
                             )
    MCDS_AREA = go.Bar(
                       x       = df['datetime'],
                       y       = df['MACDAS_diff'],
                       name    = 'MACDAS difference',
                       opacity = 0.3,
                       yaxis   = 'y2'
                       )
    MCDS_SLOPES = go.Bar(
                         x       = df['datetime'],
                         y       = df['MACDAS_slopes'],
                         name    = 'MACDAS slopes',
                         opacity = 0.3,
                         yaxis   = 'y3'
                         )

    figSignal = go.Figure()

    figSignal.add_trace(CNDSTCK)
    figSignal.add_trace(MCDS_AREA)
    figSignal.add_trace(MCDS_SLOPES)

    figSignal.update_layout(
                            title_text="BTC Bitcoin",
                            xaxis  = dict(title="Time"),
                            yaxis  = dict(
                                         title="Price -  € EUR"
                                         ),
                            yaxis2 = dict(
                                          anchor     = "x",
                                          overlaying = "y",
                                          side       = "right",
                                          position   = 0.15
                                          ),
                            yaxis3 = dict(
                                          anchor     = "x",
                                          overlaying = "y",
                                          side       = "right",
                                          position   = 0.85
                                          )
                            )

    plotly.offline.plot(figSignal, filename='Candlestick plot.html')

    return None

if __name__ == '__main__':

    main()

