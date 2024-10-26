import pandas as pd

import streamlit as st
import altair as alt

from pygwalker.api.streamlit import StreamlitRenderer, init_streamlit_comm

from types import SimpleNamespace

from df import fetch

alt.renderers.set_embed_options(theme="dark")


@st.cache_data(ttl="30m")
def fetch_asset(asset):
    return fetch(asset)

def gen_charts(asset, chart_size={"width": 560, "height": 300}):
    # Gen data
    data = fetch_asset(asset)
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
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Volume:Q"),
            color="Funds:N",
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    trading_vol_total_fig = (
        alt.Chart(etf_volumes)
        .transform_fold(
            etf_volumes.drop(columns="Date").columns.to_list(), as_=["Funds", "Volume"]
        )
        .mark_rule()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day", title="", labels=False)),
            y=alt.Y("sum(Volume):Q", title="Total Volume"),
            color=alt.value("teal"),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    # Combine trading volume and average trading volume
    trading_vol_fig = trading_vol_total_fig & trading_vol_fig
    trading_vol_fig = trading_vol_fig.properties(
        title=f"{asset} ETF trading volume",
    )

    # Net flow individual
    net_flow_individual_fig = (
        alt.Chart(etf_flow_individual)
        .transform_fold(
            etf_flow_individual.drop(columns="Date").columns.to_list(),
            as_=["Funds", "Net Flow"],
        )
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Net Flow:Q"),
            color="Funds:N",
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    net_flow_total_fig = (
        alt.Chart(etf_flow_total)
        .mark_rule()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day", title="", labels=False)),
            y=alt.Y("Total:Q"),
            color=alt.condition(
                alt.datum.Total > 0,
                alt.value("seagreen"),  # The positive color
                alt.value("orangered"),  # The negative color
            ),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    net_flow_individual_fig = net_flow_total_fig & net_flow_individual_fig
    net_flow_individual_fig = net_flow_individual_fig.resolve_scale(
        x="shared"
    ).properties(
        title=f"{asset} ETF net flow of individual funds",
    )

    net_flow_total_fig = (
        alt.Chart(etf_flow_total)
        .mark_rule()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day", title="", labels=False)),
            y=alt.Y("Total:Q"),
            color=alt.condition(
                alt.datum.Total > 0,
                alt.value("seagreen"),  # The positive color
                alt.value("orangered"),  # The negative color
            ),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    # Line chart of price
    price_fig = (
        alt.Chart(price)
        .mark_line()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day")),
            y=alt.Y("Price:Q").scale(zero=False),
            color=alt.value("crimson"),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )

    net_flow_total_fig = net_flow_total_fig & price_fig
    net_flow_total_fig = net_flow_total_fig.resolve_scale(x="shared").properties(
        title=f"{asset} ETF net flow total vs asset price",
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
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day", title="", labels=False)),
            y=alt.Y("Net Flow:Q"),
            color=alt.Color("Funds:N", scale=alt.Scale(scheme="tableau20")),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    cum_flow_individual_net_fig = cum_flow_individual_net_fig & price_fig
    cum_flow_individual_net_fig = cum_flow_individual_net_fig.resolve_scale(
        x="shared"
    ).properties(
        title=f"{asset} ETF cumulative flow of individual funds vs asset price",
    )

    # Area chart for cumulative flow
    cum_flow_total_fig = (
        alt.Chart(cum_flow_total)
        .transform_calculate(
            negative="datum.Total < 0",
        )
        .mark_area()
        .encode(
            x=alt.X("Date:T", axis=alt.Axis(tickCount="day", title="", labels=False)),
            y=alt.Y("Total:Q", impute={"value": 0}),
            color=alt.Color(
                "negative:N", title="Negative Flow", scale=alt.Scale(scheme="set2")
            ),
        )
    ).properties(
        width=chart_size["width"],
        height=chart_size["height"] / 2,
    )
    cum_flow_total_fig = cum_flow_total_fig & price_fig
    cum_flow_total_fig = cum_flow_total_fig.resolve_scale(x="shared").properties(
        title=f"{asset} ETF cumulative flow total vs asset price",
    )

    return SimpleNamespace(
        trading_vol_fig=trading_vol_fig,
        net_flow_individual_fig=net_flow_individual_fig,
        net_flow_total_fig=net_flow_total_fig,
        cum_flow_individual_net_fig=cum_flow_individual_net_fig,
        cum_flow_total_fig=cum_flow_total_fig,
    )


def asset_charts(asset: str, chart_size={"width": "container", "height": 300}):
    charts = gen_charts(asset, chart_size)
    # Vertical concat the charts in each asset into single column of that asset
    all_charts = (
        charts.trading_vol_fig
        & charts.net_flow_individual_fig
        & charts.net_flow_total_fig
        & charts.cum_flow_individual_net_fig
        & charts.cum_flow_total_fig
    ).resolve_scale(color="independent")

    return all_charts


def compound_chart(chart_size={"width": 560, "height": 300}):
    all_charts_btc = asset_charts("BTC", chart_size)
    all_charts_eth = asset_charts("ETH", chart_size)
    # Horizontal concat the charts for btc and eth
    all_charts = (all_charts_btc | all_charts_eth).resolve_scale(color="independent")

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
        chart = compound_chart(chart_size={"width": 560, "height": 300})
        # Display charts
        st.altair_chart(chart, use_container_width=True)
    with single_view:
        asset = st.selectbox(
            "Asset to view",
            ("BTC", "ETH"),
        )
        charts = gen_charts(asset, chart_size={"width": "container", "height": 600})
        st.altair_chart(charts.trading_vol_fig, use_container_width=True)
        st.altair_chart(charts.net_flow_individual_fig, use_container_width=True)
        st.altair_chart(charts.net_flow_total_fig, use_container_width=True)
        st.altair_chart(charts.cum_flow_individual_net_fig, use_container_width=True)
        st.altair_chart(charts.cum_flow_total_fig, use_container_width=True)
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
