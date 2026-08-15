from __future__ import annotations

from .core import Block, Transaction, make_block


class Miner:
    def mine(self, prev_hash: str, transactions: tuple[Transaction, ...], timestamp: int, bits: int) -> Block:
        return make_block(prev_hash, transactions, timestamp, bits)
