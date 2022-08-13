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
    "minvolatility_data",
    "riskparity_data",
]

# preprocess data
pools, hodl, apy = daily_returns()
pools, mu, cov = pool_stats(pools, (hodl + apy).iloc[-90:])  # last 90 days
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
tangency_data.index = range(len(tangency_data))

# min volatility portfolio
portfolio_return, portfolio_std, portfolio_weights = min_volatility_portfolio(mu, cov)
portfolio_weights = pd.Series(portfolio_weights, index=mu.index, name="Weight")
minvolatility_data = pd.concat(
    [
        portfolio_weights,
        data.Asset,
        data.Protocol,
    ],
    axis=1,
)
minvolatility_data["Address"] = [pool["id"] for pool in pools]
minvolatility_data = minvolatility_data.sort_values("Weight", ascending=False)
minvolatility_data.index = range(len(minvolatility_data))

# risk partity portfolio
portfolio_return, portfolio_std, portfolio_weights = risk_parity_portfolio(mu, cov)
portfolio_weights = pd.Series(portfolio_weights, index=mu.index, name="Weight")
riskparity_data = pd.concat(
    [
        portfolio_weights,
        data.Asset,
        data.Protocol,
    ],
    axis=1,
)
riskparity_data["Address"] = [pool["id"] for pool in pools]
riskparity_data = riskparity_data.sort_values("Weight", ascending=False)
riskparity_data.index = range(len(riskparity_data))

# main frontier chart
_point = pd.DataFrame(
    {
        "Return": portfolio_return,
        "Volatility": portfolio_std,
        "label": "Tangency Portfolio",
    }
)
point = (
    alt.Chart(_point)
    .mark_point(
        filled=True,
        shape="diamond",
        size=120,
        color="mediumvioletred",
    )
    .encode(
        x="Volatility:Q",
        y="Return:Q",
    )
)
text = point.mark_text(
    align="left",
    baseline="middle",
    dx=10,
).encode(text="label")

chart_frontier = (
    alt.layer(
        scatter,
        point,
        text,
        line,
    )
    .properties(
        width=500,
        height=500,
    )
    .interactive()
)

# TODO
# backtest results
# breakpoint()
