from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Tuple

MAX_HASH = (1 << 256) - 1


def canonical_bytes(value: object) -> bytes:
    """Canonical UTF-8 JSON representation used by consensus objects."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hex_hash(data: bytes) -> str:
    return sha256d(data).hex()


def merkle_root(txids: Iterable[str]) -> str:
    layer = list(txids)
    if not layer:
        return hex_hash(b"")
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [
            hex_hash(bytes.fromhex(layer[i]) + bytes.fromhex(layer[i + 1]))
            for i in range(0, len(layer), 2)
        ]
    return layer[0]


@dataclass(frozen=True)
class TxInput:
    prev_txid: str
    prev_index: int
    script_sig: str

    def to_dict(self) -> dict:
        return {"prev_txid": self.prev_txid, "prev_index": self.prev_index, "script_sig": self.script_sig}


@dataclass(frozen=True)
class TxOutput:
    value: int
    script_pubkey: str

    def to_dict(self) -> dict:
        return {"value": self.value, "script_pubkey": self.script_pubkey}


@dataclass(frozen=True)
class Transaction:
    version: int
    inputs: Tuple[TxInput, ...]
    outputs: Tuple[TxOutput, ...]
    coinbase: bool = False

    def to_dict(self, include_coinbase: bool = True) -> dict:
        result = {
            "version": self.version,
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
        }
        if include_coinbase:
            result["coinbase"] = self.coinbase
        return result

    def txid(self) -> str:
        return hex_hash(canonical_bytes(self.to_dict()))


UTXOKey = Tuple[str, int]


def validate_transaction(tx: Transaction, utxo: Mapping[UTXOKey, TxOutput]) -> None:
    if not tx.outputs:
        raise ValueError("transaction must contain at least one output")
    if any(output.value < 0 for output in tx.outputs):
        raise ValueError("negative output value")
    if tx.coinbase:
        if tx.inputs:
            raise ValueError("coinbase transaction cannot have inputs")
        return
    if not tx.inputs:
        raise ValueError("non-coinbase transaction requires inputs")
    seen = set()
    total_in = 0
    for txin in tx.inputs:
        key = (txin.prev_txid, txin.prev_index)
        if key in seen:
            raise ValueError("duplicate input")
        seen.add(key)
        previous = utxo.get(key)
        if previous is None:
            raise ValueError("missing UTXO")
        if txin.script_sig != previous.script_pubkey:
            raise ValueError("script validation failed")
        total_in += previous.value
    total_out = sum(output.value for output in tx.outputs)
    if total_out > total_in:
        raise ValueError("outputs exceed inputs")


def apply_transaction(tx: Transaction, utxo: Dict[UTXOKey, TxOutput]) -> None:
    validate_transaction(tx, utxo)
    if not tx.coinbase:
        for txin in tx.inputs:
            del utxo[(txin.prev_txid, txin.prev_index)]
    txid = tx.txid()
    for index, output in enumerate(tx.outputs):
        utxo[(txid, index)] = output


@dataclass(frozen=True)
class BlockHeader:
    version: int
    prev_hash: str
    merkle_root: str
    timestamp: int
    bits: int
    nonce: int

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "bits": self.bits,
            "nonce": self.nonce,
        }

    def serialize(self) -> bytes:
        return canonical_bytes(self.to_dict())

    def hash(self) -> str:
        return hex_hash(self.serialize())


@dataclass(frozen=True)
class Block:
    header: BlockHeader
    transactions: Tuple[Transaction, ...]

    def to_dict(self) -> dict:
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
        }

    def serialize(self) -> bytes:
        return canonical_bytes(self.to_dict())

    def hash(self) -> str:
        return self.header.hash()


def target_from_bits(bits: int) -> int:
    if not 0 < bits <= MAX_HASH:
        raise ValueError("invalid target")
    return bits


def validate_pow(header: BlockHeader) -> bool:
    target = target_from_bits(header.bits)
    return int.from_bytes(sha256d(header.serialize()), "big") <= target


def block_work(header: BlockHeader) -> int:
    target = target_from_bits(header.bits)
    return (1 << 256) // (target + 1)


def validate_block(block: Block, utxo: Mapping[UTXOKey, TxOutput], expected_prev: str | None = None) -> None:
    if expected_prev is not None and block.header.prev_hash != expected_prev:
        raise ValueError("incorrect parent")
    if not validate_pow(block.header):
        raise ValueError("invalid proof of work")
    if not block.transactions:
        raise ValueError("block must contain transactions")
    if not block.transactions[0].coinbase:
        raise ValueError("first transaction must be coinbase")
    if any(tx.coinbase for tx in block.transactions[1:]):
        raise ValueError("only first transaction may be coinbase")
    expected_root = merkle_root(tx.txid() for tx in block.transactions)
    if block.header.merkle_root != expected_root:
        raise ValueError("incorrect merkle root")
    working = dict(utxo)
    for tx in block.transactions:
        apply_transaction(tx, working)


def mine_header(template: BlockHeader) -> BlockHeader:
    nonce = template.nonce
    while nonce <= 0xFFFFFFFF:
        candidate = BlockHeader(
            version=template.version,
            prev_hash=template.prev_hash,
            merkle_root=template.merkle_root,
            timestamp=template.timestamp,
            bits=template.bits,
            nonce=nonce,
        )
        if validate_pow(candidate):
            return candidate
        nonce += 1
    raise RuntimeError("nonce space exhausted")


def make_coinbase(script_pubkey: str, value: int, marker: str = "") -> Transaction:
    return Transaction(
        version=1,
        inputs=tuple(),
        outputs=(TxOutput(value=value, script_pubkey=script_pubkey),),
        coinbase=True,
    )


def make_block(prev_hash: str, transactions: Tuple[Transaction, ...], timestamp: int, bits: int) -> Block:
    header = BlockHeader(
        version=1,
        prev_hash=prev_hash,
        merkle_root=merkle_root(tx.txid() for tx in transactions),
        timestamp=timestamp,
        bits=bits,
        nonce=0,
    )
    return Block(mine_header(header), transactions)
