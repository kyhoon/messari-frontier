import logging
from dataclasses import dataclass

import pandas as pd
from gql import Client
from gql.transport.exceptions import TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport
from gql.transport.requests import log as requests_logger
from graphql.error.graphql_error import GraphQLError

from messari.queries import (
    QueryAPYParams,
    QueryPoolsParams,
    QueryTokenWeightsParams,
    query_apy,
    query_pools,
    query_token_weights,
)

requests_logger.setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass
class Token:
    id: str
    name: str
    symbol: str


@dataclass
class Pool:
    id: str
    name: str
    tokens: list[Token]


@dataclass
class PoolSnapshot:
    id: str
    blockNumber: int
    timestamp: int
    totalValueLocked: float
    cumulativeReward: float


@dataclass
class Subgraph:
    protocol: str
    schema_type: str
    endpoint: str

    def __init_client(self):
        # initialize gql client
        url = "https://api.thegraph.com/subgraphs/name/messari/" + self.endpoint
        transport = RequestsHTTPTransport(url=url)
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

    @property
    def pools(self) -> list[Pool]:
        # create query mappings according to the schema type
        if self.schema_type == "DEX AMM":
            params = QueryPoolsParams(
                "liquidityPools",
                "inputTokens",
            )
        elif self.schema_type in ["Lending Protocol", "CDP"]:
            params = QueryPoolsParams(
                "markets",
                "inputToken",
            )
        elif self.schema_type == "Yield Aggregator":
            params = QueryPoolsParams(
                "vaults",
                "inputToken",
            )
        else:
            logger.error(f"Query for schema type {self.schema_type} is not implemented")
            raise NotImplementedError

        # fetch all pools from subgraph
        skip_id = ""
        data = []
        self.__init_client()
        while True:
            try:
                response = self.client.execute(query_pools(params, skip_id))
            except (TransportQueryError, TransportServerError, GraphQLError) as e:
                logger.error(e)
                return []

            key = list(response.keys())[0]
            result = response[key]
            if len(result) == 0:
                break
            for pool in result:
                tokens = pool[params.tokens]
                if not isinstance(tokens, list):
                    tokens = [tokens]
                tokens = [Token(**token) for token in tokens]
                data.append(
                    Pool(
                        id=pool["id"],
                        name=pool["name"],
                        tokens=tokens,
                    )
                )
            skip_id = result[-1]["id"]
        return data

    def snapshots(self, pool_id, blocks) -> list[PoolSnapshot]:
        # create query mappings according to the schema type
        if self.schema_type == "DEX AMM":
            params = QueryAPYParams(
                "liquidityPoolDailySnapshots",
                "pool",
                pool_id,
                blocks[0],
                blocks[-1],
            )
        elif self.schema_type in ["Lending Protocol", "CDP"]:
            params = QueryAPYParams(
                "marketDailySnapshots",
                "market",
                pool_id,
                blocks[0],
                blocks[-1],
            )
        elif self.schema_type == "Yield Aggregator":
            params = QueryAPYParams(
                "vaultDailySnapshots",
                "vault",
                pool_id,
                blocks[0],
                blocks[-1],
            )
        else:
            logger.error(f"Query for schema type {self.schema_type} is not implemented")
            raise NotImplementedError

        # fetch subgraph data
        skip_id = ""
        data = []
        self.__init_client()
        while True:
            try:
                response = self.client.execute(query_apy(params, skip_id))
            except (TransportQueryError, TransportServerError, GraphQLError) as e:
                logger.error(e)
                return []

            key = list(response.keys())[0]
            result = response[key]
            if len(result) == 0:
                break
            data.extend(result)
            skip_id = result[-1]["id"]

        if len(data) == 0:
            return []

        # interpolate missing data
        out = pd.DataFrame(
            None,
            index=range(blocks[0], blocks[-1] + 1),
            columns=["timestamp", "totalValueLocked", "cumulativeReward"],
        )
        for snapshot in data:
            out.loc[int(snapshot["blockNumber"])] = [
                int(snapshot["timestamp"]),
                float(snapshot["totalValueLockedUSD"]),
                float(snapshot["cumulativeSupplySideRevenueUSD"]),
            ]
        # linear interpolation
        out = out.apply(pd.to_numeric).interpolate(limit_direction="both")
        return [
            PoolSnapshot(
                id=pool_id + "_" + str(idx),
                blockNumber=idx,
                timestamp=snapshot.timestamp,
                totalValueLocked=snapshot.totalValueLocked,
                cumulativeReward=snapshot.cumulativeReward,
            )
            for idx, snapshot in out.loc[blocks].iterrows()
        ]

    def token_weights(self, pool_id) -> list[float]:
        # create query mappings according to the schema type
        if self.schema_type == "DEX AMM":
            params = QueryTokenWeightsParams(
                "liquidityPool", pool_id, "inputTokenWeights"
            )
        else:
            logger.error(f"Query for schema type {self.schema_type} is not implemented")
            raise NotImplementedError

        # fetch subgraph data
        self.__init_client()
        try:
            response = self.client.execute(query_token_weights(params))
        except (TransportQueryError, TransportServerError, GraphQLError) as e:
            logger.error(e)
            return []
        key = list(response.keys())[0]
        return list(response[key].values())[0]


subgraphs = [
    # DEX AMM
    Subgraph("Balancer v2", "DEX AMM", "balancer-v2-ethereum"),
    Subgraph("Bancor v3", "DEX AMM", "bancor-v3-ethereum"),
    Subgraph("Curve", "DEX AMM", "curve-finance-ethereum"),
    Subgraph("Saddle Finance", "DEX AMM", "saddle-finance-ethereum"),
    Subgraph("SushiSwap", "DEX AMM", "sushiswap-ethereum"),
    Subgraph("Uniswap v2", "DEX AMM", "uniswap-v2-ethereum"),
    Subgraph("Uniswap v3", "DEX AMM", "uniswap-v3-ethereum"),
    # Lending Protocols
    Subgraph("Aave v2", "Lending Protocol", "aave-v2-ethereum"),
    Subgraph("Aave ARC", "Lending Protocol", "aave-arc-ethereum"),
    Subgraph("Aave RWA", "Lending Protocol", "aave-rwa-ethereum"),
    Subgraph("Aave AMM", "Lending Protocol", "aave-amm-ethereum"),
    Subgraph("Compound", "Lending Protocol", "compound-ethereum"),
    Subgraph("CREAM Finance", "Lending Protocol", "cream-finance-ethereum"),
    Subgraph("Iron Bank", "Lending Protocol", "iron-bank-ethereum"),
    Subgraph("Maple Finance", "Lending Protocol", "maple-finance-ethereum"),
    Subgraph("Rari Fuse", "Lending Protocol", "rari-fuse-ethereum"),
    # CDPs
    Subgraph("Abracadabra", "CDP", "abracadabra-money-ethereum"),
    Subgraph("Inverse Finance", "CDP", "inverse-finance-ethereum"),
    Subgraph("Liquity", "CDP", "liquity-ethereum"),
    Subgraph("MakerDAO", "CDP", "makerdao-ethereum"),
    # Yield Aggregators
    Subgraph("Arrakis Finance", "Yield Aggregator", "arrakis-finance-ethereum"),
    Subgraph("BadgerDAO", "Yield Aggregator", "badgerdao-ethereum"),
    Subgraph("Convex Finance", "Yield Aggregator", "convex-finance-ethereum"),
    Subgraph("Gamma Strategy", "Yield Aggregator", "gamma-ethereum"),
    Subgraph("Rari Vaults", "Yield Aggregator", "rari-vaults-ethereum"),
    Subgraph("StakeDAO", "Yield Aggregator", "stake-dao-ethereum"),
    Subgraph("Tokemak", "Yield Aggregator", "tokemak-ethereum"),
    Subgraph("Vesper Finance", "Yield Aggregator", "vesper-ethereum"),
    Subgraph("Yearn v2", "Yield Aggregator", "yearn-v2-ethereum"),
]
