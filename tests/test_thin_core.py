from pathlib import Path

import pytest

from truedece.chain import Chain
from truedece.core import (
    BlockHeader,
    Transaction,
    TxInput,
    TxOutput,
    block_work,
    make_block,
    make_coinbase,
    merkle_root,
    validate_pow,
)
from truedece.node import Node

# Intentionally easy target: this is a deterministic functional control sample,
# not a production difficulty setting.
TARGET = 1 << 248


def genesis():
    tx = make_coinbase("alice", 50, marker="genesis")
    return make_block("0" * 64, (tx,), timestamp=1_700_000_000, bits=TARGET)


def child(parent, owner="alice", timestamp=1_700_000_001):
    tx = make_coinbase(owner, 50)
    return make_block(parent.hash(), (tx,), timestamp=timestamp, bits=TARGET)


def test_serialization_and_pow_are_deterministic():
    a = genesis()
    b = genesis()
    assert a.serialize() == b.serialize()
    assert a.hash() == b.hash()
    assert validate_pow(a.header)
    assert block_work(a.header) > 0


def test_transaction_utxo_transition():
    coinbase = make_coinbase("alice", 50)
    tx = Transaction(
        version=1,
        inputs=(TxInput(coinbase.txid(), 0, "alice"),),
        outputs=(TxOutput(40, "bob"), TxOutput(10, "alice")),
    )
    chain = Chain()
    g = genesis()
    chain.add_genesis(g)
    block = make_block(g.hash(), (make_coinbase("miner", 50),), timestamp=2, bits=TARGET)
    chain.add_block(block)
    # Directly exercise the transaction validator against an explicit UTXO.
    from truedece.core import apply_transaction
    utxo = {(coinbase.txid(), 0): coinbase.outputs[0]}
    apply_transaction(tx, utxo)
    assert (coinbase.txid(), 0) not in utxo
    assert (tx.txid(), 0) in utxo
    assert utxo[(tx.txid(), 1)].value == 10


def test_fork_selects_greatest_cumulative_work():
    g = genesis()
    chain = Chain()
    chain.add_genesis(g)
    a1 = child(g, "a", 2)
    b1 = child(g, "b", 3)
    chain.add_block(a1)
    chain.add_block(b1)
    a2 = child(a1, "a", 4)
    chain.add_block(a2)
    assert chain.tip_hash == a2.hash()
    assert chain.height == 2


def test_persistence_and_restart(tmp_path: Path):
    g = genesis()
    n1 = Node(tmp_path / "node")
    n1.accept_block(g)
    b1 = child(g, "alice", 2)
    n1.accept_block(b1)
    tip = n1.chain.tip_hash
    work = n1.chain.tip.cumulative_work
    utxo = n1.chain.utxo

    n2 = Node(tmp_path / "node")
    assert n2.chain.tip_hash == tip
    assert n2.chain.tip.cumulative_work == work
    assert n2.chain.utxo == utxo


def test_invalid_pow_rejected():
    g = genesis()
    bad = BlockHeader(
        version=g.header.version,
        prev_hash=g.header.prev_hash,
        merkle_root=g.header.merkle_root,
        timestamp=g.header.timestamp,
        bits=1,
        nonce=0,
    )
    assert not validate_pow(bad)
