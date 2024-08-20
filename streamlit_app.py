import streamlit as st

import pandas as pd
import yfinance as yf

import altair as alt


def clean_etf_data(df):
    """
    Clean ETF data
    """
    # Set date as index
    df.Date = pd.to_datetime(df.Date, dayfirst=True)
    df.set_index("Date", inplace=True)
    # Format index to date without time
    df.index = df.index.normalize().date
    # Format outflow to negative value
    df.replace(to_replace=r"\(([0-9.]+)\)", value=r"-\1", regex=True, inplace=True)

    # Copy original
    df_original = df.copy()

    # Replace '-' with 0
    df.replace("-", 0, inplace=True)

    # Convert from strings to numberic
    df = df.apply(pd.to_numeric)

    return df, df_original


##------------------------- ETF flow --------------------------------------------

# Get Bitcoin spot ETF history
btc_etf_flow = pd.read_html(
    "https://farside.co.uk/?p=1321", attrs={"class": "etf"}, skiprows=[1]
)[0]
# Drop column 'BTC'
# btc_etf_flow.drop(columns = ['BTC'], inplace = True)
# Remove summary lines
btc_etf_flow = btc_etf_flow.iloc[:-4]
# Extract symbols of ETF funds
btc_etf_funds = btc_etf_flow.drop(["Date", "Total"], axis=1).columns

# Get Ethereum spot ETF history
eth_etf_flow = pd.read_html(
    "https://farside.co.uk/ethereum-etf-flow-all-data/",
    attrs={"class": "etf"},
    skiprows=[2, 3],
)[0]
# Drop column index level 2
eth_etf_flow.columns = eth_etf_flow.columns.droplevel(2)
# Extract symbols of ETF funds
eth_etf_funds = eth_etf_flow.drop("Total", axis=1).columns[1:].get_level_values(1)
# Merge multi-index columns
eth_etf_flow.columns = eth_etf_flow.columns.map(" | ".join)
# Name first column "Date"
eth_etf_flow.rename(
    columns={
        "Unnamed: 0_level_0 | Unnamed: 0_level_1": "Date",
        "Total | Unnamed: 10_level_1": "Total",
    },
    inplace=True,
)
# Remove summary lines
eth_etf_flow = eth_etf_flow.iloc[:-1]

btc_etf_flow, btc_etf_flow_original = clean_etf_data(btc_etf_flow)
eth_etf_flow, eth_etf_flow_original = clean_etf_data(eth_etf_flow)

##------------------------- ETF volume -----------------------------------------

# Get BTC ETF daily volume
btc_etf_volumes = pd.DataFrame()
for fund in btc_etf_funds:
    btc_etf_volumes[fund] = yf.download(
        f"{fund}", interval="1d", period="max", start=btc_etf_flow.index[0]
    )["Volume"]

# Format index to date without time
btc_etf_volumes.index = btc_etf_volumes.index.normalize().date

# Get ETH ETF daily volume
eth_etf_volumes = pd.DataFrame()
for fund in eth_etf_funds:
    eth_etf_volumes[fund] = yf.download(
        f"{fund}", interval="1d", period="max", start=eth_etf_flow.index[0]
    )["Volume"]

# Format index to date without time
eth_etf_volumes.index = eth_etf_volumes.index.normalize().date

##------------------------- Asset price --------------------------------------------

# Get BTC price history
btc_price = yf.download(
    "BTC-USD", interval="1d", period="max", start=btc_etf_flow.index[0]
)
btc_price = btc_price.Close
# Format index to date without time
btc_price.index = btc_price.index.normalize().date

# Get ETH price history
eth_price = yf.download(
    "ETH-USD", interval="1d", period="max", start=eth_etf_flow.index[0]
)
eth_price = eth_price.Close
# Format index to date without time
eth_price.index = eth_price.index.normalize().date


if __name__ == "__main__":
    # Set page config
    st.set_page_config(layout="wide", page_icon="📈")
    # Set page title
    st.title("Crypto ETF Dashboard")

    # Sidebar to choose ETF asset to view
    st.sidebar.title("Crypto ETF Dashboard")
    # Dropdown selection to choose asset (BTC, ETH)
    asset = st.sidebar.selectbox("Choose asset", ("BTC", "ETH"))

    # Display ETF data
    if asset == "BTC":
        st.header("BTC ETF")
        etf_flow = btc_etf_flow
        etf_volumes = btc_etf_volumes
        price = btc_price
    else:
        st.header("ETH ETF")
        etf_flow = eth_etf_flow
        etf_volumes = eth_etf_volumes
        price = eth_price

    etf_flow_individual = etf_flow.drop("Total", axis=1)
    etf_flow_total = etf_flow.Total

    # Section trading volume
    st.subheader(f"{asset} ETF Trading volume")
    trading_vol_fig = (
        alt.Chart(etf_volumes.reset_index())
        .transform_fold(etf_volumes.columns, as_=["Funds", "Volume"])
        .mark_bar()
        .encode(
            x=alt.X("index:T", title="Date"),
            y=alt.Y("Volume:Q", title="Volume"),
            color="Funds:N",
        )
    )
    st.altair_chart(trading_vol_fig, use_container_width=True)

    # Section net flow individual funds
    st.subheader(f"{asset} ETF Net flow individual funds")
    net_flow_individual_fig = (
        alt.Chart(etf_flow_individual.reset_index())
        .transform_fold(
            etf_flow_individual.columns,
            as_=["Funds", "Net Flow"],
        )
        .mark_bar()
        .encode(
            x=alt.X("index:T", title="Date"),
            y=alt.Y("Net Flow:Q", title="Net Flow"),
            color="Funds:N",
        )
    )
    st.altair_chart(net_flow_individual_fig, use_container_width=True)

    # Section net flow total vs asset price
    st.subheader(f"{asset} ETF Net flow total vs asset price")
    net_flow_total_fig = (
        alt.Chart(etf_flow_total.reset_index())
        .mark_bar()
        .encode(
            x=alt.X("index:T", title="Date"),
            y=alt.Y("Total:Q"),
            color=alt.condition(
                alt.datum.Total > 0,
                alt.value("seagreen"),  # The positive color
                alt.value("orangered"),  # The negative color
            ),
        )
    )
    # Line chart of price
    price_fig = (
        alt.Chart(price.reset_index())
        .mark_line()
        .encode(
            x=alt.X("index:T", title="Date"),
            y=alt.Y("Close:Q", title="Price"),
            color=alt.value("crimson"),
        )
    )
    st.altair_chart(
        (net_flow_total_fig + price_fig).resolve_scale(
            y="independent",
        ),
        use_container_width=True,
    )

    # Section cumulative flow individual vs asset price
    st.subheader(f"{asset} ETF Cumulative flow of individual funds vs asset price")
    cum_flow_individual = etf_flow_individual.cumsum()
    # Stacking area chart of flow from individual funds
    cum_flow_individual_net_fig = (
        alt.Chart(cum_flow_individual.reset_index())
        .transform_fold(cum_flow_individual.columns, as_=["Funds", "Net Flow"])
        .mark_area()
        .encode(
            x=alt.X("index:T", title="Date"),
            y=alt.Y("Net Flow:Q", title="Net Flow"),
            color=alt.Color("Funds:N").scale(scheme="tableau20"),
        )
    )
    st.altair_chart(
        (cum_flow_individual_net_fig + price_fig).resolve_scale(y="independent"),
        use_container_width=True,
    )

    # Section cumulative flow total vs asset price
    st.subheader(f"{asset} ETF Cumulative flow total vs asset price")
    cum_flow_total = etf_flow_total.cumsum()
    # Area chart for cumulative flow
    cum_flow_total_fig = (
        alt.Chart(cum_flow_total.reset_index())
        .transform_calculate(
            negative="datum.Total < 0",
        )
        .mark_area()
        .encode(
            x=alt.X("index:T"),
            y=alt.Y("Total:Q", impute={"value": 0}),
            color=alt.Color("negative:N", title="Negative Flow").scale(
                scheme="set2"
            ),
        )
    )
    st.altair_chart(
        (cum_flow_total_fig + price_fig).resolve_scale(
            y="independent",
        ),
        use_container_width=True,
    )
