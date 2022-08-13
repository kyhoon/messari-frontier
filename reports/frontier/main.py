import os

import datapane as dp
from assets import (
    chart_frontier,
    frontier_data,
    min_volatility_data,
    risk_parity_data,
    tangency_data,
    uniform_return,
    tangency_return,
    min_volatility_return,
    risk_parity_return,
    uniform_mdd,
    tangency_mdd,
    min_volatility_mdd,
    risk_parity_mdd,
)

report = dp.Report(
    dp.Text(
        """
*Powered by [Messari Subgraphs](https://subgraphs.messari.io/) and [ypricemagic](https://github.com/BobTheBuidler/ypricemagic)*

Here we put a mind-blowing intro about how the Messari Subgraphs let us develop a unified view of various DeFi protocols.
APYs from reward tokens will be fetched from the Messari Subgraphs and the HODL values will be fetched using the mighty ypricemagic.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Efficient Frontier of DeFi Protocols

Here we describe what an efficient frontier is, what it can tell us, and what it cannot.

We also need to explain how the choice of denomination can change the interpretations.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
    ),
    dp.Group(
        dp.Group(
            dp.Text("### Efficient Frontier"),
            chart_frontier,
            label="Efficient Frontier",
        ),
        dp.Group(
            dp.Text(
                """
### Assets on the Frontier
Here we list only the assets that contribute significantly to the frontier.

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
            ),
            dp.DataTable(frontier_data),
            label="Assets on the Frontier",
        ),
        columns=2,
    ),
    dp.Text(
        """
Brief explanation about the numbers and the axes

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
    ),
    dp.Text("### Backtest Results"),
    dp.Text("#### Monthly Return"),
    dp.Group(
        dp.BigNumber(
            heading="Uniform Portfolio",
            value=f"{round(uniform_return * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Tangency Portfolio",
            value=f"{round(tangency_return * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Min Volatility Portfolio",
            value=f"{round(min_volatility_return * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Risk Parity Portfolio",
            value=f"{round(risk_parity_return * 100, 2)}%",
        ),
        columns=4,
    ),
    dp.Text("#### Maximum Drawdown"),
    dp.Group(
        dp.BigNumber(
            heading="Uniform Portfolio",
            value=f"{round(uniform_mdd * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Tangency Portfolio",
            value=f"{round(tangency_mdd * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Min Volatility Portfolio",
            value=f"{round(min_volatility_mdd * 100, 2)}%",
        ),
        dp.BigNumber(
            heading="Risk Parity Portfolio",
            value=f"{round(risk_parity_mdd * 100, 2)}%",
        ),
        columns=4,
    ),
    dp.Text(
        """
Description of the backtesting method and the exemplary portfolios

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
    ),
    dp.Text("### Portfolio Structure"),
    dp.Select(
        blocks=[
            dp.DataTable(tangency_data, label="Tangency Portfolio"),
            dp.DataTable(min_volatility_data, label="Min Volatility Portfolio"),
            dp.DataTable(risk_parity_data, label="Risk Parity Portfolio"),
        ]
    ),
    dp.Text(
        """
Share reference, additional links, disclaimers

Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
"""
    ),
)


if __name__ == "__main__":
    dp.login(token=os.environ["DATAPANE_TOKEN"])
    report.upload(name="DeFi Frontier", publicly_visible=True)
