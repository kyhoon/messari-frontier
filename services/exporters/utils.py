import os
from datetime import datetime

import brownie
from brownie.network.state import Chain

os.environ["BROWNIE_NETWORK_ID"] = "mainnet"
brownie._config.CONFIG.settings["autofetch_sources"] = True

from ypricemagic.magic import magic

chain = Chain()


def binary_search(low, high, dt, tol=600):
    if high >= low:
        mid = (high + low) // 2
        block = chain[mid]
        block_dt = datetime.fromtimestamp(block.timestamp)
        diff = int((dt - block_dt).total_seconds())
        if abs(diff) < tol:
            return mid
        elif diff > 0:
            return binary_search(mid, high, dt, tol=tol)
        else:
            return binary_search(low, mid, dt, tol=tol)
    else:
        return -1


def datetime_to_block(dt):
    latest = chain[-1]["number"]
    return binary_search(0, latest, dt)


def get_prices(addresses, block):
    return magic.get_prices(addresses, block, fail_to_None=True, silent=False)
