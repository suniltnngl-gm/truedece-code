from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .core import Block, BlockHeader, Transaction, TxInput, TxOutput


def block_to_json(block: Block) -> dict:
    return block.to_dict()


def block_from_json(data: dict) -> Block:
    header_data = data["header"]
    header = BlockHeader(**header_data)
    transactions = []
    for tx_data in data["transactions"]:
        inputs = tuple(TxInput(**item) for item in tx_data["inputs"])
        outputs = tuple(TxOutput(**item) for item in tx_data["outputs"])
        transactions.append(Transaction(version=tx_data["version"], inputs=inputs, outputs=outputs, coinbase=tx_data["coinbase"]))
    return Block(header=header, transactions=tuple(transactions))


class Storage:
    """Small deterministic filesystem store for the THIN-CORE-001 baseline."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.blocks = self.root / "blocks"
        self.blocks.mkdir(parents=True, exist_ok=True)
        self.meta = self.root / "meta.json"

    def put_block(self, block: Block) -> None:
        path = self.blocks / f"{block.hash()}.json"
        if not path.exists():
            path.write_text(json.dumps(block_to_json(block), sort_keys=True, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    def iter_blocks(self) -> Iterable[Block]:
        for path in sorted(self.blocks.glob("*.json")):
            yield block_from_json(json.loads(path.read_text(encoding="utf-8")))

    def put_tip(self, block_hash: str) -> None:
        self.meta.write_text(json.dumps({"tip": block_hash}, sort_keys=True, separators=(",", ":")), encoding="utf-8")

    def get_tip(self) -> str | None:
        if not self.meta.exists():
            return None
        return json.loads(self.meta.read_text(encoding="utf-8")).get("tip")
