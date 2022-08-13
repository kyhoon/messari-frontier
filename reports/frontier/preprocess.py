import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlmodel import Session, select

sys.path.insert(1, os.path.join(sys.path[0], "..", ".."))

from database.engine import engine
from database.models import Pool, PoolSnapshot, TokenSnapshot
from messari.subgraphs import subgraphs


def load_pool_data():
    with Session(engine) as session:
        # load pool data from database
        statement = select(PoolSnapshot.pool_id).where(PoolSnapshot.pool_id != None)
        pool_ids = set(session.exec(statement).all())
        pools = [session.get(Pool, pool_id) for pool_id in pool_ids]

        # load token data for each pool
        pool_info, pool_data = [], []
        for pool in pools:
            # pool token prices
            subgraph = [s for s in subgraphs if s.protocol == pool.protocol][0]
            prices = []
            for token in pool.tokens:
                statement = select(TokenSnapshot).where(
                    TokenSnapshot.token_id == token.id
                )
                token_snapshots = session.exec(statement).all()
                prices.append(
                    pd.Series(
                        [snapshot.price for snapshot in token_snapshots],
                        index=[snapshot.timestamp for snapshot in token_snapshots],
                        dtype=float,
                    )
                )
            prices = pd.DataFrame(prices).T.sort_index()
            if len(prices) == 0:
                continue

            # apply token weights if the pool has multiple tokens
            if len(prices.columns) > 1:
                try:
                    token_weights = np.asarray(
                        subgraph.token_weights(pool.id), dtype=float
                    )
                except Exception as e:
                    token_weights = np.ones(len(pool.tokens))
                if len(token_weights) != len(pool.tokens):
                    token_weights = np.ones(len(pool.tokens))
                token_weights /= token_weights.sum()
                prices = prices @ token_weights
            else:
                prices = prices[0]
            prices.name = pool.name

            # pool tvl and rewards
            statement = select(
                PoolSnapshot.timestamp,
                PoolSnapshot.totalValueLocked,
                PoolSnapshot.cumulativeReward,
            ).where(PoolSnapshot.pool_id == pool.id)
            values = session.exec(statement).all()
            index, tvls, rewards = list(zip(*values))
            if len(index) == 0:
                continue

            tvls = pd.Series(tvls, index=index, dtype=float).sort_index()
            tvls = tvls[~tvls.index.duplicated(keep="first")]
            tvls.name = pool.name
            rewards = pd.Series(rewards, index=index, dtype=float).sort_index()
            rewards = rewards[~rewards.index.duplicated(keep="first")]
            rewards.name = pool.name

            pool_info.append(pool.__dict__)
            pool_data.extend([prices, tvls, rewards])

    return pool_info, pool_data


def daily_returns():
    # load pool data
    pool_info, pool_data = load_pool_data()

    # resample daily data for the last 90 days
    pool_data = pd.DataFrame(pool_data).T
    pool_data.index = pd.to_datetime(pool_data.index, unit="s")
    pool_data = pool_data.resample("1D").last().iloc[-90:]

    pools, hodl, apy = [], [], []
    for idx in range(0, len(pool_info)):
        _pool_data = pool_data.iloc[:, 3 * idx : 3 * idx + 3]
        if _pool_data.iloc[-1].isna().any():
            continue
        _pool_data = _pool_data.interpolate(limit_direction="both")

        # pool info
        pools.append(pool_info[idx])

        # hodl
        _prices = _pool_data.iloc[:, 0]
        _hodl = _prices.pct_change()
        hodl.append(_hodl)

        # apy
        _tvls = _pool_data.iloc[:, 1]
        _rewards = _pool_data.iloc[:, 2]
        _apy = _rewards.diff() / _tvls.shift()
        apy.append(_apy)

    hodl = pd.DataFrame(hodl).T.iloc[1:]
    apy = pd.DataFrame(apy).T.iloc[1:]
    apy.replace([np.inf, -np.inf], 0.0, inplace=True)
    apy.fillna(0.0, inplace=True)
    pools = pd.Series(pools, index=hodl.columns)
    return pools, hodl, apy


def pool_stats(pools, returns):
    T = 365  # yearly stats
    mu = (1 + returns).prod() ** (T / len(returns)) - 1
    cov = returns.cov() * T
    sigma = np.sqrt(np.diag(cov))

    # remove outliers
    mu_iqr = np.quantile(mu, 0.75) - np.quantile(mu, 0.25)
    mu_median = np.median(mu)
    mask = (mu > mu_median + 1.5 * mu_iqr) | (mu < mu_median - 1.5 * mu_iqr)

    sigma_iqr = np.quantile(sigma, 0.75) - np.quantile(sigma, 0.25)
    sigma_median = np.median(sigma)
    mask |= (sigma > sigma_median + 1.5 * sigma_iqr) | (
        sigma < sigma_median - 1.5 * sigma_iqr
    )

    pools = pools[~mask]
    mu = mu[~mask]
    cov = returns.loc[:, ~mask].cov() * T
    return pools, mu, cov


def efficient_frontier(mu, cov, num_samples=100, threshold=0.1):
    # maximize return given the target std
    def efficient_return(target_std):
        N = len(mu)

        def neg_portfolio_return(weights):
            return -(mu * weights).sum()

        def portfolio_std(weights):
            return np.sqrt(
                (weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum()
            )

        constraints = (
            {"type": "eq", "fun": lambda x: portfolio_std(x) - target_std},
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},
        )
        bounds = tuple((0, 1) for _ in range(N))
        result = minimize(
            neg_portfolio_return, N * [1 / N], bounds=bounds, constraints=constraints
        )
        return -result.fun, result.x

    sigma = np.sqrt(np.diag(cov))
    xs = np.linspace(sigma.min(), sigma.max(), num_samples)
    ys, nonzero = [], set({})
    last_y = 0.0
    for idx in range(num_samples):
        new_y, weights = efficient_return(xs[idx])
        nonzero.update(set(*np.nonzero(weights > threshold)))
        if new_y >= last_y:
            last_y = new_y
            ys.append(new_y)
        else:  # early stopping
            break

    return xs[: len(ys)], ys, nonzero


def tangency_portfolio(mu, cov):
    # maximize sharpe ratio
    def neg_sharpe_ratio(weights):
        # assuming risk-free rate of 3%
        rf = 0.03
        portfolio_return = (mu * weights).sum()
        portfolio_std = np.sqrt(
            (weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum()
        )
        return -(portfolio_return - rf) / portfolio_std

    N = len(mu)
    constraints = ({"type": "eq", "fun": lambda x: np.sum(x) - 1},)
    bounds = tuple((0, 1) for _ in range(N))
    result = minimize(
        neg_sharpe_ratio, N * [1 / N], bounds=bounds, constraints=constraints
    )
    weights = result.x
    portfolio_return = (mu * weights).sum()
    portfolio_std = np.sqrt(
        (weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum()
    )
    return portfolio_return, portfolio_std, weights


def min_volatility_portfolio(mu, cov):
    # minimize volatility
    def volatility(weights):
        return np.sqrt((weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum())

    N = len(mu)
    constraints = ({"type": "eq", "fun": lambda x: np.sum(x) - 1},)
    bounds = tuple((0, 1) for _ in range(N))
    result = minimize(volatility, N * [1 / N], bounds=bounds, constraints=constraints)
    weights = result.x
    portfolio_return = (mu * weights).sum()
    portfolio_std = np.sqrt(
        (weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum()
    )
    return portfolio_return, portfolio_std, weights


def risk_parity_portfolio(mu, cov):
    sigma = np.sqrt(np.diag(cov))
    weights = 1 / sigma
    weights /= weights.sum()
    portfolio_return = (mu * weights).sum()
    portfolio_std = np.sqrt(
        (weights[np.newaxis, :] @ cov @ weights[:, np.newaxis]).sum()
    )
    return portfolio_return, portfolio_std, weights
