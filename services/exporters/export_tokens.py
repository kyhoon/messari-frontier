import logging
import logging.config
import os
import signal
import sys

from brownie import chain
from rich.progress import track
from sqlmodel import Session

sys.path.insert(1, os.path.join(sys.path[0], "..", ".."))

from utils import get_prices

from database.engine import engine
from database.models import Pool, Token
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

        # update the list of tokens
        for subgraph in subgraphs:
            logger.info(f"Fetching pools from {subgraph.protocol}")
            pools = subgraph.pools
            logger.info(f"Fetched {len(pools)} pools from {subgraph.protocol}")

            for pool in track(pools, description=subgraph.protocol):
                # check if price exists
                tokens = [Token(**token.__dict__) for token in pool.tokens]
                addresses = [token.id for token in pool.tokens]
                try:
                    prices = get_prices(addresses, block.number)
                except Exception as e:
                    logger.debug(e)
                    continue

                # remove pool and tokens if price does not exist
                if any(price is None for price in prices):
                    with Session(engine) as session:
                        _pool = session.get(Pool, pool.id)
                        if _pool is not None:
                            session.delete(_pool)
                        for address in addresses:
                            _token = session.get(Token, address)
                            if _token is not None:
                                session.delete(_token)
                        session.commit()
                    continue

                # add new pool
                with Session(engine) as session:
                    if session.get(Pool, pool.id) is not None:
                        continue
                    tokens = []
                    for token in pool.tokens:
                        _token = session.get(Token, token.id)
                        if _token is None:
                            tokens.append(Token(**token.__dict__))
                        else:
                            tokens.append(_token)
                    session.add(
                        Pool(
                            id=pool.id,
                            name=pool.name,
                            protocol=subgraph.protocol,
                            tokens=tokens,
                        )
                    )
                    session.commit()


if __name__ == "__main__":
    main()
