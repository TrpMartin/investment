# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Display changes in Millionærklubben portfolios from website
# - a cronjob downloads each day the portfolios into a CSV from https://www.home.saxo/da-dk/campaigns/millionaerklubben
# - this notebook turns the CSV files into a visual representation
# - we also calculate returns, however, without cash data this is only based on the stock valu, because the chash number gets not published
# - run this as Streamlit app with `streamlit run <this file>`

# +
import pandas as pd
import numpy as np
import os
import glob
import dateutil.parser as dparser
import datetime as dt
import streamlit as st

import matplotlib.pyplot as plt
import plotly.express as px
import matplotlib.dates as mdates
import matplotlib.patches as patches

from mystockmodule import retrievals, conversions

# %matplotlib inline
# -

## constants
DATA_DIR = './data/' # this is where the portfolio CSV files are being downloaded
if os.path.isdir(DATA_DIR):
    print("Dir exists")
else:
    print("Dir not exisitng")
    DATA_DIR = '/home/pi/mynotebooks/projects/investment/mill_klubben/data/'
SQL_MK_PRICE_PATH = 'sqlite:///'+DATA_DIR+'MK_PRICES.db'

mycolors=[
        "#0068c9",
        "#83c9ff",
        "#ff2b2b",
        "#ffabab",
        "#29b09d",
        "#7defa1",
        "#ff8700",
        "#ffd16a",
        "#6d3fc0",
        "#d5dae5",
    ]

st.title("Millionærklubben portfolios")

# # Prepare data from website downloads

today = dt.date.today()
yesterday = (today - dt.timedelta(days=1))
#round to decimals in pandas tables output
pd.options.display.float_format = '{:,.2f}'.format

if os.path.isdir(DATA_DIR):

    # use glob to get all the csv files in the folder path = os.getcwd()
    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    
    df = pd.DataFrame()
    dates = []
    # loop over the list of csv files
    for f in csv_files:
        # print the location and filename
        #print('Reading file:', f.split("\\")[-1]) #debug. Will be read in non-order. 
          
        # read the csv file
        x = pd.read_csv(f, sep=';', index_col=[0])
        extracted_date = dparser.parse(f, fuzzy=True) # date parser from file name. No date in the CSV. Maybe add this in 2024?
        x['Date'] = extracted_date
        dates.append(extracted_date.isoformat()) 
        df = pd.concat([x,df], axis=0)
    
    #dates.sort()
    
    df = df.sort_values('Date').reset_index(drop=True)
    ## Note: "Amount" is calculated during scraping from Antal * Åbningspris
else:
    print("NO DIRECTORY!")
    pass

# +
# fix naming errors on website
df.loc[(df.Instrument == 'AKERBP'), 'Instrument'] = 'AKRBP'
df.loc[(df.Instrument == 'ALKb'), 'Instrument'] = 'ALK_B'
df.loc[(df.Instrument == 'BEL'), 'Instrument'] = 'BELCO'
df.loc[(df.Instrument == 'ATOS'), 'Instrument'] = 'ATO'
df.loc[(df.Instrument == 'NOVOb'), 'Instrument'] = 'NOVO_B'
df.loc[(df.Instrument == 'NOVO-B'), 'Instrument'] = 'NOVO_B'
df.loc[(df.Instrument == 'NZYMb'), 'Instrument'] = 'NZYM_B'
df.loc[(df.Instrument == 'NZYM-B'), 'Instrument'] = 'NZYM_B'
df.loc[(df.Instrument == 'MAERSKb'), 'Instrument'] = 'MAERSK_B'
df.loc[(df.Instrument == 'GOMX_TR'), 'Antal'] = df.Antal/3 # was a 1/3 split (Lau)
df.loc[(df.Instrument == 'GOMX_TR'), 'Instrument'] = 'GOMX'
df.loc[(df.Ticker == 'GOMX-TR.ST'), 'Ticker'] = 'GOMX.ST'
df.loc[(df.Instrument == 'CARLb'), 'Instrument'] = 'CARL_B'
df.loc[(df.Ticker == 'CARLb.CO'), 'Ticker'] = 'CARL-B.CO'

## Delisted must be removed it is just simpler this way
df = df.drop(df[df.Instrument == 'VOYG'].index) # Voyager got delisted
df = df.drop(df[df.Instrument == 'EURN'].index) # I cannot get price data :-(
df = df.drop(df[df.Instrument == 'TEST'].index) # Michael bought & sold TEST, but I cannot get prices because I do not know from which stock exchange
df = df.drop(df[df.Instrument == 'LOCK-A017'].index) # no idea what that was
df = df.drop(df[df.Instrument == 'TEN_NEW'].index) # Lau bytte aktier
df = df.drop(df[df.Instrument == 'ALCC'].index) ## delisted?
# the price in Milan is the same as in Germany
df.Instrument = df.Instrument.replace({'INRG':'IQQH'}) # cannot download data for iShares Clean energy from Milan
#df = df.drop(df[df.Instrument == 'INRG'].index) # cannot download data for iShares Clean energy from Milan
df = df.sort_values('Date').reset_index(drop=True)

# +
##sorted(df.Instrument.unique())
# -

# ## FX for DKK conversion

# +
## this is made during each websitedownload
#df['Amount'] = df.Antal * df.Åbningspris

fx = {'USD':7.058, 'EUR':7.456, 'DKK':1, 'SEK':0.645, 'AUD':4.49, 'CAD':5.19, 'NOK':0.657}

df['FX'] = df['Currency'].map(fx)

#df.tail()
# -

# ## Add Anders Bæk (fix)
# From Dec 28 to Jan 4 the webpage was not updated. I make a df adjustment from Jan 1st to Jan 4th to compensate.

# +
anders_start_portfolio = df[(df.Investor ==  'Anders Bæk') & (df.Date == '2024-01-05')].sort_values('Ticker')#.loc[:,['Ticker', 'PurchaseDKK']]

## duplicate Anders' portfolio from the 5th for all dates prior; from 1st to 4th all is the same, dirty fix, but works
to_add = pd.DataFrame()
for i in range(1,5):
    df_temp = anders_start_portfolio.drop(columns='Date').reset_index(drop=True)
    df_temp['Date'] = dt.datetime(2024,1,i)
    to_add = pd.concat([to_add, df_temp], ignore_index=True)

df = pd.concat([to_add, df], axis=0).reset_index(drop=True).sort_index()
# -

# ## Master df 'm' with all dates
# - Remove Mads Christensen, I do not find his strategy and actions relevant

## remove Mads Christiansen - since Jan 2024 anyway no longer in MK
my_investors = ['Lars Persson', 'Lau Svenssen', 'Michael Friis Jørgensen', 'Anders Bæk']
m = df.loc[df.Investor.isin(my_investors)].sort_values('Investor').sort_index()
#m.tail()
#m.loc[m.Instrument == 'SVITZR']
#Investor	Instrument	Antal	Åbningspris	Amount	Currency	Stockexchange	Ticker	FX	Date	BuyDate	LastSeen
m = m.rename(columns={'Åbningspris':'OpeningPrice', 'Antal':'Quantity'})

# # Select Start Date

sd = st.date_input("Start date of analysis", value=dt.datetime(2024,1,1), min_value=dt.datetime(2024,1,1), 
                   max_value=dt.datetime.today(), 
                   format="YYYY-MM-DD", disabled=False, label_visibility="visible")
# show table with the selected start date
m = m[m.Date >= pd.to_datetime(sd)]
#m.tail()

# Group by 'Instrument' and find the first appearing and last date
## MAGIC !! first and last are applied functions??
buy_sell_dates = m.reset_index().groupby(['Investor','Instrument']).agg({'Date': ['first', 'last']})
buy_sell_dates.columns = buy_sell_dates.columns.droplevel(0)
buy_sell_dates = buy_sell_dates.rename(columns={'last':'LastSeen', 'first':'BuyDate'})
#buy_sell_dates.tail()

## add the first and last seen dates
mbs = m.set_index(['Investor', 'Instrument']).merge(
    buy_sell_dates, right_index=True, left_index=True, how='outer').reset_index()

# ## Prices
# have this here, so the streamlit is loaded

# +
prices = retrievals.sql_price(list(m.Instrument.unique()), SQL_MK_PRICE_PATH )
prices = prices.sort_index()

## make consecutive, because I have some Buys that are on weekends (website update)
prices = conversions.create_full_date_df(prices).loc[sd:] # also limit to selected date 'sd'

prices = prices.reindex(sorted(prices.columns), axis=1)

## create df that contains the FX for multiplying later with prices
fx_df = pd.DataFrame(data=m[['Instrument', 'FX']]).drop_duplicates().set_index('Instrument').sort_index()

# -

len(prices.columns)

## multiplying did not work as I wanted, this is a method that works 
## IMPORTANT that the dfs are sorted and same length
dkk_prices = pd.DataFrame(prices.values*fx_df.T.values, columns=prices.columns, index=prices.index).dropna(how='all')

# ## Quantity

## create pivot df that has all stock quantity per date
q = mbs.pivot_table(index='Date', columns=['Investor', 'Instrument'], values='Quantity').sort_index().dropna(how='all', axis=1)
#q.tail()


# ## Value

# +
## create value df and the sum of invested stocks per investor per date
## this is in stock currency still
value = q.multiply(dkk_prices, level=1, axis='columns').drop_duplicates().dropna(how='all').sort_index()

value_per_investor = value.T.groupby(level=0).sum().T.sort_index()
# -

## make some lists
all_tickers = df.Ticker.unique()
all_investors = df.Investor.unique()
## I originally deselected Mads Christiansen 
my_investors = m.Investor.unique()
my_tickers = m.Ticker.unique()
my_instruments = m.Instrument.unique()

# # Overview all investors

st.subheader("Overview all investors")

fig, ax = plt.subplots(figsize=[12,6])
ax.plot(value_per_investor)
ax.set_title('Value of investments without Cash')
ax.legend(value_per_investor.columns)
ax.set_ylabel('DKK')
fig.show();
st.pyplot(fig)

# +
## Now with all investors
curr_all = mbs.groupby(['Investor','Instrument']).last()
curr_all['InvestedDKK'] = curr_all.Amount * curr_all.FX

curr_all = curr_all.loc[curr_all.Date == curr_all['LastSeen']].reset_index()

for i in range(0, len(curr_all)):
    buy_price = prices.loc[curr_all.BuyDate[i], curr_all.Instrument[i]]
    sell_price = prices.loc[curr_all.LastSeen[i], curr_all.Instrument[i]]
    #print("Buy price of", trans.Instrument[i], "was", round(buy_price, 2), "on", trans.Buy[i])
    curr_all.loc[i, 'BuyPrice'] = buy_price
    curr_all.loc[i, 'LastPrice'] = sell_price
    curr_all.loc[i, 'Return'] = ((float(sell_price)-buy_price)/buy_price)       

## NVIDIA fix split during holding this stock
curr_all.loc[curr_all.Instrument == 'NVDA', 'BuyPrice' ] = curr_all['BuyPrice'].loc[curr_all.Instrument == 'NVDA'] /10 

curr_all['AfkastDKK'] = curr_all.InvestedDKK * curr_all.Return
curr_all['Days'] = curr_all.LastSeen - curr_all.BuyDate


# +
data = curr_all[['Investor','Instrument','Return']].copy().sort_values('Return')
data.Return = data.Return * 100
## show plotly plot
fig = px.bar(data, x="Return", y="Instrument", orientation='h', color='Investor', 
             hover_data=['Return', 'Instrument'],
             color_discrete_sequence=mycolors, width=1000, height=600)
# overwrite tick labels    
fig.update_layout(
    yaxis = {
     'tickmode': 'array',
     #'tickvals': list(range(len(data.MyName))),
     'ticktext': data.Instrument.str.slice(stop=14).tolist()
    },
    margin=dict(l=200)
)

#fig.show()
# Plot!
st.plotly_chart(fig, use_container_width=True)
# -

# # Show Selected Investor

st.sidebar.header("Drilldowns")
#st.sidebar.markdown("""
#Show the portfolio per Millionærklubben investor
#""")
selected_investor = st.sidebar.selectbox('Select investor', my_investors)

## Show portfolio content
t = "Portfolio of " + selected_investor
st.subheader(t, divider='rainbow')

## portfolio of selected investor
curr_si = curr_all.loc[(curr_all.Investor == selected_investor) & (curr_all.Quantity >0) &
                        (curr_all.LastSeen == pd.to_datetime(today))].copy()
curr_si['ReturnPct'] = curr_si.Return * 100
st.dataframe(curr_si[['Instrument', 'Quantity', 'InvestedDKK', 'Days', 'ReturnPct', 'AfkastDKK']])

# ## Invested and Afkast

# +
# Plot the Buy and Sell bar chart
investor_colors = {'Lars Persson': 'c', 'Lau Svenssen': 'm', 'Mads Christiansen': 'y', 'Michael Friis Jørgensen': 'b', 'Anders Bæk': 'orange'}

## PLOT
fig = plt.figure(figsize=[14,12])
ax0 = plt.subplot(121)

for index, row in curr_all.iterrows():
    ax0.barh(y=row['Instrument'], width=row['Days'], left=row['BuyDate'], color=investor_colors[row['Investor']])

# Make ticks on occurrences of each month:
ax0.set_title('Holding period')
ax0.xaxis.set_major_locator(mdates.MonthLocator())
# Get only the month to show in the x-axis:
ax0.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax0.set_xlabel('Timeline')
ylim = ax0.get_ylim()
ax0.vlines(today, ylim[0], ylim[1], colors='r')
ax0.xaxis.grid(True, alpha=0.5)

#------ second plot
ax1 = plt.subplot(122, sharey=ax0)

## the trades
for index, row in curr_all.iterrows():
    ax1.barh(y=row['Instrument'], width=row['InvestedDKK']/1000, left=0, color='grey', alpha=0.6)

## only the currently helt stocks
for index, row in curr_all.loc[curr_all.LastSeen == today.strftime('%Y-%m-%d')].iterrows():
    ax1.barh(y=row['Instrument'], width=row['InvestedDKK']/1000, left=0, color=investor_colors[row['Investor']], alpha=0.9)

ax1.set_title("Invested for DKK")
ax1.xaxis.grid(True, alpha=0.5)
ax1.yaxis.tick_right()
ax1.set_xlabel('TDKK')

plt.gca().invert_yaxis()

# Adding a legend
patch = []
for i in investor_colors:
    patch.append(patches.Patch(color=investor_colors[i]))
ax1.legend(handles=patch, labels=investor_colors.keys(), fontsize=11)

plt.savefig(fname='portfolio_movements.png', dpi=150, transparent=None)
plt.show();
st.pyplot(fig=plt, clear_figure=None, use_container_width=True)
# -

bs = curr_all.copy()
## example how to show the portfolio of a certain investor
#bs.loc[bs.Investor == 'Lau Svenssen']

# ## Sold or bought during the last X days?

st.header("Sold and Bought")

# +
# get first and last datetime for final week of data
days = 14
range_max = bs['LastSeen'].max()# - dt.timedelta(days=1) # that should be today, or yesterday, if the cronjob runs as expected and I run this in the evening or during the day, respectively
range_min = range_max - dt.timedelta(days=days)

# take slice with final week of data
rec_sold = bs[(bs['LastSeen'] >= range_min) &
              (bs['LastSeen'] <= range_max) &
              (bs['Quantity'] == 0)].reset_index(drop=True)

range_max = bs['BuyDate'].max() # that should be today, or yesterday, if the cronjob runs as expected and I run this in the evening or during the day, respectively
range_min = range_max - dt.timedelta(days=days)

# take slice with final week of data
rec_buy = bs[(bs['BuyDate'] >= range_min) & 
             (bs['BuyDate'] <= range_max) &
             (bs['Quantity'] > 0)].reset_index(drop=True)

# +
cols = ['Investor', 'Instrument', 'Days', 'Quantity', 'InvestedDKK', 'Return']
st.text("Stocks that have been sold the last "+str(days)+" days:")

if rec_sold.empty:
    st.text("No stocks have been sold!")
else:
    st.dataframe(rec_sold.loc[:, cols])

# +
st.text("Stocks that have been bought the last "+str(days)+" days:")

if rec_buy.empty:
    st.text("No stocks have been bought!")
else:
    st.dataframe(rec_buy.loc[:, cols])
# -

# ## Plot the stock price graphs with buy and sell events

# +
## mask the prices, so they fit with the buy and sells and are not too long back in history
date_frame_days = 10 # days before and after 
range_min = bs['BuyDate'].min() - dt.timedelta(days=date_frame_days)
range_max = bs['LastSeen'].max() + dt.timedelta(days=date_frame_days)

mask = (prices.index >= range_min) & (prices.index < range_max)
masked_prices = prices.loc[mask, rec_sold.Instrument].sort_index().dropna(how='all') ########## use this df for masked price analysis
# -

for i in rec_sold.index:
    fig, ax = plt.subplots(figsize=[8,4])
    ax.set_title(rec_sold.Investor[i]+" sold last week ")
    ax.plot(masked_prices.iloc[:,i], label=rec_sold.Instrument[i])
    ax.scatter(rec_sold.BuyDate[i], rec_sold.BuyPrice[i], color='g', s=60, marker='v')
    ax.scatter(rec_sold.LastSeen[i], rec_sold.LastPrice[i], color='r', s=60)
    ax.text(rec_sold.LastSeen[i], rec_sold.LastPrice[i]*1.02, s=str(round(rec_sold.Return[i]*100,1))+"%")
    ax.legend()
fig.show();
## problem, if nothing sold, then the last figure (the big plot) is shown instead of the plot form the code above
#st.pyplot(fig=fig, clear_figure=None, use_container_width=True)



# +
#df.loc[df.Instrument == 'RAY_B']
# -








