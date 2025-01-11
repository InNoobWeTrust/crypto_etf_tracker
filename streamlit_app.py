import pandas as pd

import streamlit as st
from streamlit.components.v1 import iframe
import altair as alt

from pygwalker.api.streamlit import StreamlitRenderer, init_streamlit_comm

from types import SimpleNamespace

from df import fetch

alt.renderers.set_embed_options(theme="dark")


@st.cache_data(ttl="30m")
def fetch_asset(asset):
    return fetch(asset)

def gen_charts(asset, chart_size={"width": 560, "height": 150}):
    # Gen data
    data = fetch_asset(asset)
    etf_volumes = data.etf_volumes
    price = data.price
    etf_flow_individual = data.etf_flow_individual
    etf_flow_total = data.etf_flow_total
    cum_flow_individual = data.cum_flow_individual
    cum_flow_total = data.cum_flow_total

    # Create bindings for interval selection
    scale_selection = alt.selection_interval(encodings=["x"],bind="scales")

    # Line chart of price
    price = (
        alt.Chart(price)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Price:Q").scale(zero=False),
            color=alt.value("crimson"),
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )

    trading_vol_individual = (
        alt.Chart(etf_volumes)
        .transform_fold(
            etf_volumes.drop(columns="Date").columns.to_list(), as_=["Funds", "Volume"]
        )
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Volume:Q", title="Trading Volume Individual"),
            color="Funds:N",
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )
    trading_vol_total = (
        alt.Chart(etf_volumes)
        .transform_fold(
            etf_volumes.drop(columns="Date").columns.to_list(), as_=["Funds", "Volume"]
        )
        .mark_rule()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("sum(Volume):Q", title="Trading Volume Total"),
            color=alt.value("teal"),
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )

    # Net flow individual
    net_flow_individual = (
        alt.Chart(etf_flow_individual)
        .transform_fold(
            etf_flow_individual.drop(columns="Date").columns.to_list(),
            as_=["Funds", "Net Flow"],
        )
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Net Flow:Q", title="Net Flow Individual"),
            color="Funds:N",
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )
    net_flow_total = (
        alt.Chart(etf_flow_total)
        .mark_rule()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Total:Q", title="Net Flow Total"),
            color=alt.condition(
                alt.datum.Total > 0,
                alt.value("seagreen"),  # The positive color
                alt.value("orangered"),  # The negative color
            ),
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )

    # Stacking area chart of flow from individual funds
    cum_flow_individual = (
        alt.Chart(cum_flow_individual)
        .transform_fold(
            cum_flow_individual.drop(columns="Date").columns.to_list(),
            as_=["Funds", "Net Flow"],
        )
        .mark_area()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Net Flow:Q", title="Cumulative Flow Individual"),
            color=alt.Color("Funds:N", scale=alt.Scale(scheme="tableau20")),
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )

    # Area chart for cumulative flow
    cum_flow_total = (
        alt.Chart(cum_flow_total)
        .transform_calculate(
            negative="datum.Total < 0",
        )
        .mark_area()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount={"interval": "month", "step": 1}), title=""),
            y=alt.Y("Total:Q", title="Cumulative Flow Total", impute={"value": 0}),
            color=alt.Color(
                "negative:N", title="Negative Flow", scale=alt.Scale(scheme="set2")
            ),
        )
    ).add_params(scale_selection).properties(
        width=chart_size["width"],
        height=chart_size["height"],
    )

    return SimpleNamespace(
        price=price,
        trading_vol_individual=trading_vol_individual,
        trading_vol_total=trading_vol_total,
        net_flow_individual=net_flow_individual,
        net_flow_total=net_flow_total,
        cum_flow_individual=cum_flow_individual,
        cum_flow_total=cum_flow_total,
    )

def asset_charts(asset: str, chart_size={"width": "container", "height": 150}):
    charts = gen_charts(asset, chart_size)

    # Vertical concat the charts in each asset into single column of that asset
    all_charts = (
        charts.price
        & charts.trading_vol_individual
        & charts.trading_vol_total
        & charts.net_flow_individual
        & charts.net_flow_total
        & charts.cum_flow_individual
        & charts.cum_flow_total
    ).resolve_scale(
        color="independent",
    ).properties(
        title=f"{asset} ETF",
    )

    return all_charts

if __name__ == "__main__":
    # Set page config
    st.set_page_config(layout="wide", page_icon="📈")
    # Initialize pygwalker communication
    init_streamlit_comm()

    dashboard_tab, single_view, flow_tab, volume_tab, price_tab = st.tabs(
        [
            "Dashboard",
            "View Single ETF",
            "Explore ETF Flow",
            "Explore ETF Volume",
            "Explore ETF Asset Price",
        ]
    )

    btc = fetch_asset("BTC")
    eth = fetch_asset("ETH")

    with dashboard_tab:
        btc_charts = asset_charts("BTC", chart_size={"width": "container", "height": 150})
        eth_charts = asset_charts("ETH", chart_size={"width": "container", "height": 150})
        # Display charts
        btc_chart_col, eth_chart_col = st.columns(2)
        with btc_chart_col:
            st.altair_chart(btc_charts, use_container_width=True)
        with eth_chart_col:
            st.altair_chart(eth_charts, use_container_width=True)
        # Display iframes
        btc_col, eth_col = st.columns(2)
        with btc_col:
            iframe(btc.url, height=1200, scrolling=True)
        with eth_col:
            iframe(eth.url, height=1200, scrolling=True)
    with single_view:
        asset = st.selectbox(
            "Asset to view",
            ("BTC", "ETH"),
        )
        charts = asset_charts(asset, chart_size={"width": "container", "height": 300})
        st.altair_chart(charts, use_container_width=True)
        iframe(fetch_asset(asset).url, height=1200, scrolling=True)
    with flow_tab:
        btc_flow, eth_flow = btc.etf_flow, eth.etf_flow
        btc_flow["Asset"] = "BTC"
        eth_flow["Asset"] = "ETH"
        df = pd.concat([btc_flow, eth_flow])
        df.Date = df.Date.astype(str)
        StreamlitRenderer(df).explorer()
    with volume_tab:
        btc_volume, eth_volume = btc.etf_volumes, eth.etf_volumes
        btc_volume["Asset"] = "BTC"
        eth_volume["Asset"] = "ETH"
        df = pd.concat([btc_volume, eth_volume])
        df.Date = df.Date.astype(str)
        StreamlitRenderer(df).explorer()
    with price_tab:
        btc_price, eth_price = btc.price, eth.price
        btc_price["Asset"] = "BTC"
        eth_price["Asset"] = "ETH"
        df = pd.concat([btc_price, eth_price])
        df.Date = df.Date.astype(str)
        StreamlitRenderer(df).explorer()
