from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .core import Block, TxOutput, UTXOKey, apply_transaction, block_work, validate_block


@dataclass
class ChainEntry:
    block: Block
    height: int
    cumulative_work: int
    utxo: Dict[UTXOKey, TxOutput]


class Chain:
    """Minimal fork-capable chain index using cumulative proof-of-work."""

    def __init__(self) -> None:
        self.entries: Dict[str, ChainEntry] = {}
        self.children: Dict[str, set[str]] = {}
        self.tip_hash: Optional[str] = None

    def add_genesis(self, block: Block) -> str:
        if self.entries:
            raise ValueError("genesis already exists")
        working: Dict[UTXOKey, TxOutput] = {}
        validate_block(block, working, expected_prev="0" * 64)
        for tx in block.transactions:
            apply_transaction(tx, working)
        block_hash = block.hash()
        self.entries[block_hash] = ChainEntry(block, 0, block_work(block.header), working)
        self.children[block_hash] = set()
        self.tip_hash = block_hash
        return block_hash

    def add_block(self, block: Block) -> str:
        block_hash = block.hash()
        if block_hash in self.entries:
            return block_hash
        parent = self.entries.get(block.header.prev_hash)
        if parent is None:
            raise ValueError("unknown parent")
        validate_block(block, parent.utxo, expected_prev=block.header.prev_hash)
        working = dict(parent.utxo)
        for tx in block.transactions:
            apply_transaction(tx, working)
        entry = ChainEntry(
            block=block,
            height=parent.height + 1,
            cumulative_work=parent.cumulative_work + block_work(block.header),
            utxo=working,
        )
        self.entries[block_hash] = entry
        self.children.setdefault(block.header.prev_hash, set()).add(block_hash)
        self.children.setdefault(block_hash, set())
        if self._better(block_hash, self.tip_hash):
            self.tip_hash = block_hash
        return block_hash

    def _better(self, candidate: str, current: Optional[str]) -> bool:
        if current is None:
            return True
        a = self.entries[candidate]
        b = self.entries[current]
        if a.cumulative_work != b.cumulative_work:
            return a.cumulative_work > b.cumulative_work
        # Deterministic equal-work rule: lexicographically smaller block hash wins.
        return candidate < current

    @property
    def tip(self) -> ChainEntry:
        if self.tip_hash is None:
            raise ValueError("chain has no genesis")
        return self.entries[self.tip_hash]

    @property
    def utxo(self) -> Dict[UTXOKey, TxOutput]:
        return dict(self.tip.utxo)

    @property
    def height(self) -> int:
        return self.tip.height
