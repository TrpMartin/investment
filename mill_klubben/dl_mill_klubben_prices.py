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

# # Get stock prices of Millionaerklubben portfolios
# - get all stocks ever traded
# - dowload price data with Yahooquery and update the SQL

import os
import glob
import dateutil.parser as dparser
import pandas as pd
from time import sleep
from mystockmodule import retrievals, definitions, conversions
import datetime as dt
import numpy as np

ex_dict = {
    'xcse': '.CO',
    'xmil': '.MI', # eigentlich Milan
    'xosl': '.OL',
    'xome': '.ST',
    'xhel': '.HE',
    'xetr': '.DE',
    'xams': '.AS',
    'xpar': '.PA',
    'xnys': '',
    'xtse': '.TO',
    'xtsx': '',
    'xasx': '.AX',
    'xlon': '.L',
    'xnas': ''
          }

DATA_DIR = '/home/pi/mynotebooks/data/MK_files/'
today = dt.date.today()
yesterday = (today - dt.timedelta(days=1))
#round to decimals in pandas tables output
pd.options.display.float_format = '{:,.2f}'.format

# +
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

dates.sort()
df = df.sort_values('Date').reset_index(drop=True)

# -

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
df.loc[(df.Instrument == 'INRGxmil'), 'Instrument'] = 'IQQH' # cannot download original Milan data of this ETF
df.loc[(df.Instrument == 'INRG'), 'Instrument'] = 'IQQH' # cannot download original Milan data of this ETF
df.loc[(df.Instrument == 'IQQH'), 'Stockexchange'] = 'xetr' # but the IQQH is the same approx.
df.loc[(df.Instrument == 'IQQH'), 'Ticker'] = 'IQQH.DE'
df.loc[(df.Instrument == 'GOMX_TR'), 'Antal'] = df.Antal/3 # was a 1/3 split (Lau)
df.loc[(df.Instrument == 'GOMX_TR'), 'Instrument'] = 'GOMX'
df.loc[(df.Ticker == 'GOMX-TR.ST'), 'Ticker'] = 'GOMX.ST'
df.loc[(df.Instrument == 'CARLb'), 'Instrument'] = 'CARL_B'
df.loc[(df.Ticker == 'CARLb.CO'), 'Ticker'] = 'CARL-B.CO'


# +
#sorted(df.Instrument.unique())
# -

# make a new dataframe 'dl' which contains only the unique tickers for stock price downloading
dl = df[['Instrument', 'Ticker']].copy().drop_duplicates().reset_index(drop=True)

# +
##problem
##dl = dl.loc[dl['Instrument'] == 'ALCC'].reset_index() ## ah does not exist any longer
# -

for i in range(0,len(dl)):
    res = retrievals.yq_price_importer(dl.loc[i,'Ticker'], dl.loc[i,'Instrument'], 
                                   db_path=definitions.SQL_MK_PRICE_PATH)

print("MK stock prices download finished!")


