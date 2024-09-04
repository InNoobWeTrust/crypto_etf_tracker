import pandas as pd
import yfinance as yf

import streamlit as st
import altair as alt

from types import SimpleNamespace

alt.renderers.set_embed_options(theme="dark")


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

    # Convert from strings to numberic
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


##------------------------- ETF flow --------------------------------------------

# Get Bitcoin spot ETF history
btc_etf_flow = pd.read_html(
    "https://farside.co.uk/?p=1321", attrs={"class": "etf"}, skiprows=[1]
)[0]
# Remove summary lines
btc_etf_flow = btc_etf_flow.iloc[:-4]
# Extract symbols of ETF funds
btc_etf_funds = btc_etf_flow.drop(["Date", "Total"], axis=1).columns.to_list()

# Get Ethereum spot ETF history
eth_etf_flow = pd.read_html(
    "https://farside.co.uk/ethereum-etf-flow-all-data/",
    attrs={"class": "etf"},
    skiprows=[2, 3],
)[0]
# Drop column index level 2
eth_etf_flow.columns = eth_etf_flow.columns.droplevel(2)
# Extract symbols of ETF funds
eth_etf_funds = (
    eth_etf_flow.drop("Total", axis=1).columns[1:].get_level_values(1).to_list()
)
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

# Extract Date column from index
btc_etf_volumes = extract_date_index(btc_etf_volumes)

# Get ETH ETF daily volume
eth_etf_volumes = pd.DataFrame()
for fund in eth_etf_funds:
    eth_etf_volumes[fund] = yf.download(
        f"{fund}", interval="1d", period="max", start=eth_etf_flow.index[0]
    )["Volume"]

# Extract Date column from index
eth_etf_volumes = extract_date_index(eth_etf_volumes)

##------------------------- Asset price --------------------------------------------

# Get BTC price history
btc_price = yf.download(
    "BTC-USD", interval="1d", period="max", start=btc_etf_flow["Date"][0]
)
btc_price = btc_price.Close
# Extract Date column from index
btc_price = extract_date_index(btc_price)

# Get ETH price history
eth_price = yf.download(
    "ETH-USD", interval="1d", period="max", start=eth_etf_flow["Date"][0]
)
eth_price = eth_price.Close
# Extract Date column from index
eth_price = extract_date_index(eth_price)


def gen_data(asset):
    if asset == "BTC":
        etf_volumes = btc_etf_volumes
        price = btc_price

        etf_flow_individual = btc_etf_flow.drop(columns="Total")
        etf_flow_total = btc_etf_flow[["Date", "Total"]]
    else:
        etf_volumes = eth_etf_volumes
        price = eth_price

        etf_flow_individual = eth_etf_flow.drop(columns="Total")
        etf_flow_total = eth_etf_flow[["Date", "Total"]]

    cum_flow_individual = etf_flow_individual.drop(columns="Date").cumsum()
    cum_flow_individual["Date"] = etf_flow_individual.Date
    cum_flow_total = pd.DataFrame(
        {
            "Date": etf_flow_total.Date,
            "Total": etf_flow_total.Total.cumsum(),
        }
    )

    return SimpleNamespace(
        etf_volumes=etf_volumes,
        price=price,
        etf_flow_individual=etf_flow_individual,
        etf_flow_total=etf_flow_total,
        cum_flow_individual=cum_flow_individual,
        cum_flow_total=cum_flow_total,
    )


def gen_charts(asset, chart_size={"width": 560, "height": 300}):
    # Gen data
    data = gen_data(asset)
    etf_volumes = data.etf_volumes
    price = data.price
    etf_flow_individual = data.etf_flow_individual
    etf_flow_total = data.etf_flow_total
    cum_flow_individual = data.cum_flow_individual
    cum_flow_total = data.cum_flow_total

    trading_vol_fig = (
        alt.Chart(etf_volumes)
        .transform_fold(
            etf_volumes.drop(columns="Date").columns.to_list(), as_=["Funds", "Volume"]
        )
        .mark_bar()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Volume:Q"),
            color="Funds:N",
        )
    )
    trading_vol_avg_fig = (
        alt.Chart(etf_volumes)
        .transform_fold(
            etf_volumes.drop(columns="Date").columns.to_list(), as_=["Funds", "Volume"]
        )
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("mean(Volume):Q", title="Average Volume"),
            color=alt.value("crimson"),
        )
    )
    # Combine trading volume and average trading volume
    trading_vol_fig += trading_vol_avg_fig
    trading_vol_fig = trading_vol_fig.properties(
        title=f"{asset} ETF trading volume",
        **chart_size,
    )

    # Net flow individual
    net_flow_individual_fig = (
        alt.Chart(etf_flow_individual)
        .transform_fold(
            etf_flow_individual.drop(columns="Date").columns.to_list(),
            as_=["Funds", "Net Flow"],
        )
        .mark_bar()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Net Flow:Q"),
            color="Funds:N",
        )
    )
    net_flow_total_line_fig = (
        alt.Chart(etf_flow_total)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Total:Q"),
            color=alt.value("crimson"),
        )
    )
    net_flow_individual_fig += net_flow_total_line_fig
    net_flow_individual_fig = net_flow_individual_fig.properties(
        title=f"{asset} ETF net flow of individual funds",
        **chart_size,
    )

    net_flow_total_fig = (
        alt.Chart(etf_flow_total)
        .mark_bar()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
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
        alt.Chart(price)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Close:Q", title="Price"),
            color=alt.value("crimson"),
        )
    )

    net_flow_total_fig += price_fig
    net_flow_total_fig = net_flow_total_fig.resolve_scale(
        y="independent",
    ).properties(
        title=f"{asset} ETF net flow total vs asset price",
        **chart_size,
    )

    # Stacking area chart of flow from individual funds
    cum_flow_individual_net_fig = (
        alt.Chart(cum_flow_individual)
        .transform_fold(
            cum_flow_individual.drop(columns="Date").columns.to_list(),
            as_=["Funds", "Net Flow"],
        )
        .mark_area()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Net Flow:Q"),
            color=alt.Color("Funds:N", scale=alt.Scale(scheme="tableau20")),
        )
    )
    cum_flow_individual_net_fig += price_fig
    cum_flow_individual_net_fig = cum_flow_individual_net_fig.resolve_scale(
        y="independent",
    ).properties(
        title=f"{asset} ETF cumulative flow of individual funds vs asset price",
        **chart_size,
    )

    # Area chart for cumulative flow
    cum_flow_total_fig = (
        alt.Chart(cum_flow_total)
        .transform_calculate(
            negative="datum.Total < 0",
        )
        .mark_area()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Total:Q", impute={"value": 0}),
            color=alt.Color(
                "negative:N", title="Negative Flow", scale=alt.Scale(scheme="set2")
            ),
        )
    )
    cum_flow_total_fig += price_fig
    cum_flow_total_fig = cum_flow_total_fig.resolve_scale(
        y="independent",
    ).properties(
        title=f"{asset} ETF cumulative flow total vs asset price",
        **chart_size,
    )

    return SimpleNamespace(
        trading_vol_fig=trading_vol_fig,
        net_flow_individual_fig=net_flow_individual_fig,
        net_flow_total_fig=net_flow_total_fig,
        cum_flow_individual_net_fig=cum_flow_individual_net_fig,
        cum_flow_total_fig=cum_flow_total_fig,
    )


def compound_chart(chart_size={"width": 560, "height": 300}):
    btc_charts = gen_charts("BTC", chart_size)
    eth_charts = gen_charts("ETH", chart_size)

    # Vertical concat the charts in each asset into single colume of that asset
    all_charts_btc = (
        btc_charts.trading_vol_fig
        & btc_charts.net_flow_individual_fig
        & btc_charts.net_flow_total_fig
        & btc_charts.cum_flow_individual_net_fig
        & btc_charts.cum_flow_total_fig
    ).resolve_scale(color="independent")
    all_charts_eth = (
        eth_charts.trading_vol_fig
        & eth_charts.net_flow_individual_fig
        & eth_charts.net_flow_total_fig
        & eth_charts.cum_flow_individual_net_fig
        & eth_charts.cum_flow_total_fig
    ).resolve_scale(color="independent")
    # Horizontal concat the charts for btc and eth
    all_charts = (all_charts_btc | all_charts_eth).resolve_scale(color="independent")

    return all_charts


if __name__ == "__main__":
    # Set page config
    st.set_page_config(layout="wide", page_icon="📈")

    chart = compound_chart(chart_size={"width": 560, "height": 300})
    # Display charts
    st.altair_chart(chart, use_container_width=True)
