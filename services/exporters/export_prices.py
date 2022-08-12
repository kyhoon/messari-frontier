import logging
import logging.config
import os
import signal
import sys
from datetime import datetime, timedelta

import pandas as pd
from brownie import chain
from rich.progress import track
from sqlmodel import Session, select

sys.path.insert(1, os.path.join(sys.path[0], "..", ".."))

from utils import datetime_to_block, get_prices

from database.engine import engine
from database.models import Pool, PoolSnapshot, Token, TokenSnapshot
from messari.subgraphs import subgraphs

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def handle_signal(*args) -> None:
    logger.error("Interrupted by user")
    sys.exit()


def main():
    # handle signals
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    for block in chain.new_blocks(height_buffer=1000):
        logger.info(f"Starting loop for block {block.number}")

        # create snapshots for blocks closest to midnight in UTC
        dt = datetime.fromtimestamp(block.timestamp)
        dt = datetime.combine(dt, datetime.min.time()) - timedelta(days=59)
        blocks = [datetime_to_block(dt) for dt in pd.date_range(dt, periods=60)]

        # update pool data
        logger.info("Fetching pools from database")
        with Session(engine) as session:
            pools = session.exec(select(Pool)).all()
            logger.info(f"Fetched {len(pools)} pools from database")
            for pool in pools:
                subgraph = [s for s in subgraphs if s.protocol == pool.protocol][0]
                snapshots = subgraph.snapshots(pool.id, blocks)
                # skip if no change in values
                if (
                    len(snapshots) == 0
                    or snapshots[0].cumulativeReward == snapshots[-1].cumulativeReward
                ):
                    continue

                for snapshot in snapshots:
                    # pool may disappear due to the token exporter
                    if (
                        session.get(PoolSnapshot, snapshot.id) is not None
                        or session.get(Pool, pool.id) is None
                    ):
                        continue
                    session.add(PoolSnapshot(**snapshot.__dict__, pool=pool))
                session.commit()

        # fetch tokens from top 50 pools with high tvl
        logger.info("Fetching tokens for pools with high TVL")
        addresses = set({})
        with Session(engine) as session:
            statement = (
                select(PoolSnapshot)
                .where(PoolSnapshot.blockNumber == blocks[-1])
                .order_by(PoolSnapshot.totalValueLocked.desc())
                .limit(50)
            )
            for snapshot in session.exec(statement).all():
                addresses.update([token.id for token in snapshot.pool.tokens])
        addresses = list(addresses)
        logger.info(f"Fetched {len(addresses)} tokens")

        # fetch prices
        logger.info("Fetching prices of tokens")
        for block in track(blocks, description="prices"):
            try:
                prices = get_prices(addresses, block)
            except Exception as e:
                logger.error(e)
                continue
            with Session(engine) as session:
                for address, price in zip(addresses, prices):
                    price_id = address + "_" + str(block)
                    if session.get(TokenSnapshot, price_id) is not None:
                        continue
                    session.add(
                        TokenSnapshot(
                            id=price_id,
                            blockNumber=block,
                            price=price,
                            token=session.get(Token, address),
                        )
                    )
                session.commit()


if __name__ == "__main__":
    main()
