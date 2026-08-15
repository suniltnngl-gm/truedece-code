from __future__ import annotations

from pathlib import Path

from .chain import Chain
from .core import Block
from .storage import Storage


class Node:
    """Consensus/storage integration boundary for THIN-CORE-001."""

    def __init__(self, data_dir: str | Path) -> None:
        self.storage = Storage(data_dir)
        self.chain = Chain()
        self._restore()

    def _restore(self) -> None:
        blocks = list(self.storage.iter_blocks())
        if not blocks:
            return
        genesis = next((b for b in blocks if b.header.prev_hash == "0" * 64), None)
        if genesis is None:
            raise ValueError("stored chain has no genesis")
        self.chain.add_genesis(genesis)
        pending = {b.hash(): b for b in blocks if b.hash() != genesis.hash()}
        while pending:
            progressed = False
            for block_hash, block in list(pending.items()):
                if block.header.prev_hash in self.chain.entries:
                    self.chain.add_block(block)
                    del pending[block_hash]
                    progressed = True
            if not progressed:
                raise ValueError("stored chain contains an unresolved parent")
        stored_tip = self.storage.get_tip()
        if stored_tip is not None and stored_tip in self.chain.entries:
            self.chain.tip_hash = stored_tip

    def accept_block(self, block: Block) -> str:
        block_hash = self.chain.add_genesis(block) if self.chain.tip_hash is None else self.chain.add_block(block)
        self.storage.put_block(block)
        self.storage.put_tip(self.chain.tip_hash)
        return block_hash
