import altair as alt
import numpy as np
import pandas as pd
from preprocess import (
    daily_returns,
    efficient_frontier,
    min_volatility_portfolio,
    pool_stats,
    risk_parity_portfolio,
    tangency_portfolio,
)

__all__ = [
    "chart_frontier",
    "frontier_data",
    "tangency_data",
    "min_volatility_data",
    "risk_parity_data",
]


# preprocess data
pools, hodl, apy = daily_returns()
returns = (hodl + apy).iloc[-90:]  # last 90 days
pools, mu, cov = pool_stats(pools, returns)
sigma = np.sqrt(np.diag(cov))


# efficient frontier
xs, ys, nonzero = efficient_frontier(mu, cov)
data = pd.DataFrame(
    np.stack([mu, sigma]).T, columns=["Return", "Volatility"], index=mu.index
)
data["Asset"] = [pool["name"] for pool in pools]
data["Protocol"] = [pool["protocol"] for pool in pools]
data["Address"] = [pool["id"] for pool in pools]
data["OnFrontier"] = False
for idx in nonzero:
    data.loc[data.index[idx], "OnFrontier"] = True

frontier_data = data[data["OnFrontier"]].reset_index()
frontier_data = frontier_data[["Asset", "Protocol", "Address", "Return", "Volatility"]]

scatter = (
    alt.Chart(data)
    .mark_circle(size=70)
    .encode(
        x="Volatility",
        y="Return",
        color=alt.Color(
            "OnFrontier",
            scale=alt.Scale(
                domain=[True, False],
                range=["mediumvioletred", "cornflowerblue"],
            ),
            legend=alt.Legend(title="On Frontier"),
        ),
        tooltip=["Return", "Volatility", "Asset", "Protocol"],
    )
)
_line = pd.DataFrame(
    {
        "Return": ys,
        "Volatility": xs,
    }
)
line = (
    alt.Chart(_line)
    .mark_line(
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
    )
)


# uniform portfolio
uniform_point = (
    alt.Chart(
        pd.DataFrame(
            {
                "Return": [mu.mean()],
                "Volatility": [np.sqrt(cov.mean().mean())],
                "label": "Uniform Portfolio",
            }
        )
    )
    .mark_point(
        filled=True,
        shape="diamond",
        size=120,
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
        tooltip=["Return", "Volatility"],
    )
)
uniform_text = uniform_point.mark_text(
    align="left",
    baseline="middle",
    dx=10,
).encode(text="label")


# tangency portfolio
portfolio_return, portfolio_std, portfolio_weights = tangency_portfolio(mu, cov)
portfolio_weights = pd.Series(portfolio_weights, index=mu.index, name="Weight")
tangency_data = pd.concat(
    [
        portfolio_weights,
        data.Asset,
        data.Protocol,
    ],
    axis=1,
)
tangency_data["Address"] = [pool["id"] for pool in pools]
tangency_data = tangency_data.sort_values("Weight", ascending=False)
tangency_data = tangency_data[tangency_data.Weight > 1e-3]
tangency_data.index = range(len(tangency_data))

tangency_point = (
    alt.Chart(
        pd.DataFrame(
            {
                "Return": portfolio_return,
                "Volatility": portfolio_std,
                "label": "Tangency Portfolio",
            }
        )
    )
    .mark_point(
        filled=True,
        shape="diamond",
        size=120,
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
        tooltip=["Return", "Volatility"],
    )
)
tangency_text = tangency_point.mark_text(
    align="left",
    baseline="middle",
    dx=10,
).encode(text="label")


# min volatility portfolio
portfolio_return, portfolio_std, portfolio_weights = min_volatility_portfolio(mu, cov)
portfolio_weights = pd.Series(portfolio_weights, index=mu.index, name="Weight")
min_volatility_data = pd.concat(
    [
        portfolio_weights,
        data.Asset,
        data.Protocol,
    ],
    axis=1,
)
min_volatility_data["Address"] = [pool["id"] for pool in pools]
min_volatility_data = min_volatility_data.sort_values("Weight", ascending=False)
min_volatility_data = min_volatility_data[min_volatility_data.Weight > 1e-3]
min_volatility_data.index = range(len(min_volatility_data))

min_volatility_point = (
    alt.Chart(
        pd.DataFrame(
            {
                "Return": portfolio_return,
                "Volatility": portfolio_std,
                "label": "Min Volatility Portfolio",
            }
        )
    )
    .mark_point(
        filled=True,
        shape="diamond",
        size=120,
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
        tooltip=["Return", "Volatility"],
    )
)
min_volatility_text = min_volatility_point.mark_text(
    align="left",
    baseline="middle",
    dx=10,
).encode(text="label")


# risk parity portfolio
portfolio_return, portfolio_std, portfolio_weights = risk_parity_portfolio(mu, cov)
portfolio_weights = pd.Series(portfolio_weights, index=mu.index, name="Weight")
risk_parity_data = pd.concat(
    [
        portfolio_weights,
        data.Asset,
        data.Protocol,
    ],
    axis=1,
)
risk_parity_data["Address"] = [pool["id"] for pool in pools]
risk_parity_data = risk_parity_data.sort_values("Weight", ascending=False)
risk_parity_data = risk_parity_data[risk_parity_data.Weight > 1e-3]
risk_parity_data.index = range(len(risk_parity_data))

risk_parity_point = (
    alt.Chart(
        pd.DataFrame(
            {
                "Return": portfolio_return,
                "Volatility": portfolio_std,
                "label": "Risk Parity Portfolio",
            }
        )
    )
    .mark_point(
        filled=True,
        shape="diamond",
        size=120,
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
        tooltip=["Return", "Volatility"],
    )
)
risk_parity_text = risk_parity_point.mark_text(
    align="left",
    baseline="middle",
    dx=10,
).encode(text="label")


# main frontier chart
chart_frontier = (
    alt.layer(
        scatter,
        uniform_point,
        uniform_text,
        tangency_point,
        tangency_text,
        min_volatility_point,
        min_volatility_text,
        risk_parity_point,
        risk_parity_text,
        line,
    )
    .properties(
        width=500,
        height=500,
    )
    .interactive()
)


# backtest results
start, end = -120, -30
pools, hodl, apy = daily_returns()
_, mu, cov = pool_stats(pools, (hodl + apy).iloc[start:end])  # 90 days window
_, _, _tangency_weights = tangency_portfolio(mu, cov)
_, _, _min_volatility_weights = min_volatility_portfolio(mu, cov)
_, _, _risk_parity_weights = risk_parity_portfolio(mu, cov)

returns = (hodl + apy).iloc[end:][mu.index]  # previous 30 days
_uniform_return = (1 + returns.mean(axis=1)).cumprod()
uniform_return = _uniform_return[-1] - 1
uniform_mdd = (_uniform_return / _uniform_return.cummax() - 1).min()

_tangency_return = (1 + (returns * _tangency_weights).sum(axis=1)).cumprod()
tangency_return = _tangency_return[-1] - 1
tangency_mdd = (_tangency_return / _tangency_return.cummax() - 1).min()

_min_volatility_return = (1 + (returns * _min_volatility_weights).sum(axis=1)).cumprod()
min_volatility_return = _min_volatility_return[-1] - 1
min_volatility_mdd = (
    _min_volatility_return / _min_volatility_return.cummax() - 1
).min()

_risk_parity_return = (1 + (returns * _risk_parity_weights).sum(axis=1)).cumprod()
risk_parity_return = _risk_parity_return[-1] - 1
risk_parity_mdd = (_risk_parity_return / _risk_parity_return.cummax() - 1).min()
