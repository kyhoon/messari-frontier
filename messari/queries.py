import logging
from dataclasses import dataclass

from gql import gql

logger = logging.getLogger(__name__)


@dataclass
class QueryPoolsParams:
    pools: str
    tokens: str


def query_pools(params: QueryPoolsParams, skip_id: str = ""):
    return gql(
        f"""
        {{
            {params.pools} (
                first: 1000,
                where: {{
                    id_gt: "{skip_id}"
                }}
            ) {{
                id
                name
                {params.tokens} {{
                    id
                    name
                    symbol
                }}
            }}
        }}
        """
    )


@dataclass
class QueryAPYParams:
    snapshots: str
    pool: str
    pool_id: str
    from_block: int
    to_block: int


def query_apy(params: QueryAPYParams, skip_id=""):
    return gql(
        f"""
        {{
            {params.snapshots} (
                first: 1000,
                where: {{
                    id_gt: "{skip_id}"
                    {params.pool}: "{params.pool_id}"
                    blockNumber_gte: {params.from_block}
                    blockNumber_lte: {params.to_block}
                }}
            ) {{
                id
                blockNumber
                timestamp
                totalValueLockedUSD
                cumulativeSupplySideRevenueUSD
            }}
        }}
        """
    )


@dataclass
class QueryTokenWeightsParams:
    pool: str
    pool_id: str
    token_weights: str


def query_token_weights(params: QueryTokenWeightsParams):
    return gql(
        f"""
        {{
            {params.pool} (
                id: "{params.pool_id}"
            ) {{
                {params.token_weights}
            }}
        }}
        """
    )
