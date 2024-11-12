import pandas as pd
import pytz
import requests
import yfinance as yf

from typing import List
from types import SimpleNamespace


def clean_etf_data(df):
    """
    Clean ETF data
    """
    # Copy original
    df_original = df.copy()
    # Set date as index
    df_original["Date"] = pd.to_datetime(df_original["Date"])

    # Format outflow to negative value
    df = df.drop(columns="Date")
    df.replace(to_replace=r"\(([0-9.]+)\)", value=r"-\1", regex=True, inplace=True)

    # Replace '-' with 0
    df.replace("-", 0, inplace=True)

    # Convert from strings to numeric
    df = df.apply(pd.to_numeric)
    df["Date"] = df_original["Date"]

    return df, df_original


def extract_date_index(df):
    """
    Extract index from dataframe as Date
    """
    # Convert Series to DataFrame
    if isinstance(df, pd.Series):
        df = df.to_frame()
    df = df.reset_index(names="Date")
    # Set date as index
    df.Date = pd.to_datetime(df.Date)

    return df

FETCH_HEADER = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

def fetch_btc_etf():
    url = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
    r = requests.Session().get(
        url,
        headers=FETCH_HEADER,
    )
    # Get Bitcoin spot ETF history
    btc_etf_flow = pd.read_html(
        r.content,
        attrs={"class": "etf"},
        skiprows=[1],
    )[0]
    # Remove summary lines
    btc_etf_flow = btc_etf_flow.iloc[:-4]
    # Extract symbols of ETF funds
    btc_etf_funds = btc_etf_flow.drop(columns=["Date", "Total"]).columns.to_list()

    btc_etf_flow, btc_etf_flow_original = clean_etf_data(btc_etf_flow)

    return SimpleNamespace(
        url=url,
        flow=btc_etf_flow,
        orig=btc_etf_flow_original,
        funds=btc_etf_funds,
    )


def fetch_eth_etf():
    url = "https://farside.co.uk/ethereum-etf-flow-all-data/"
    r = requests.Session().get(
        url,
        headers=FETCH_HEADER,
    )
    # Get Ethereum spot ETF history
    eth_etf_flow = pd.read_html(
        r.content,
        attrs={"class": "etf"},
        skiprows=[2, 3],
    )[0]
    # Drop column index level 2
    eth_etf_flow.columns = eth_etf_flow.columns.droplevel(2)
    # Extract symbols of ETF funds
    eth_etf_funds = (
        eth_etf_flow.drop(columns="Total").columns[1:].get_level_values(1).to_list()
    )
    # Merge multi-index columns
    eth_etf_flow.columns = eth_etf_flow.columns.map(" - ".join)
    # Name first column "Date"
    eth_etf_flow.rename(
        columns={
            "Unnamed: 0_level_0 - Unnamed: 0_level_1": "Date",
            "Total - Unnamed: 10_level_1": "Total",
        },
        inplace=True,
    )
    # Remove summary lines
    eth_etf_flow = eth_etf_flow.iloc[:-1]
    eth_etf_flow, eth_etf_flow_original = clean_etf_data(eth_etf_flow)

    return SimpleNamespace(
        url=url,
        flow=eth_etf_flow,
        orig=eth_etf_flow_original,
        funds=eth_etf_funds,
    )


def fetch_etf_volumes(funds: List[str], start_time=None):
    etf_volumes = pd.DataFrame()
    for fund in funds:
        etf_volumes[fund] = yf.download(
            str(fund),
            interval="1d",
            period="max",
            start=start_time,
        )["Volume"]
    etf_volumes = extract_date_index(etf_volumes)

    return etf_volumes


def fetch_asset_price(ticker: str, start_time=None):
    price = yf.download(ticker, interval="1d", period="max", start=start_time)["Close"]
    price = extract_date_index(price)
    price.rename(columns={"Close": "Price"}, inplace=True)

    return price


def fetch(asset):
    if asset == "BTC":
        df = fetch_btc_etf()
    else:
        df = fetch_eth_etf()

    etf_flow, etf_funds, etf_url = df.flow, df.funds, df.url
    tz = pytz.timezone("America/New_York")

    etf_flow, etf_funds = df.flow, df.funds
    tz = pytz.timezone("America/New_York")
    start_time = tz.localize(etf_flow.Date[0])
    etf_volumes = fetch_etf_volumes(etf_funds, start_time=start_time)
    price = fetch_asset_price(f"{asset}-USD", start_time=start_time)

    etf_flow_individual = etf_flow.drop(columns="Total")
    etf_flow_total = etf_flow[["Date", "Total"]]

    cum_flow_individual = etf_flow_individual.drop(columns="Date").cumsum()
    cum_flow_individual["Date"] = etf_flow_individual.Date
    cum_flow_total = pd.DataFrame(
        {
            "Date": etf_flow_total.Date,
            "Total": etf_flow_total.Total.cumsum(),
        }
    )

    return SimpleNamespace(
        url=etf_url,
        etf_flow=etf_flow,
        etf_volumes=etf_volumes,
        price=price,
        etf_flow_individual=etf_flow_individual,
        etf_flow_total=etf_flow_total,
        cum_flow_individual=cum_flow_individual,
        cum_flow_total=cum_flow_total,
    )
