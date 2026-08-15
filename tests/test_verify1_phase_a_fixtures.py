from __future__ import annotations

import json
from pathlib import Path

from truedece.core import BlockHeader, Transaction, TxInput, TxOutput, make_block, make_coinbase, merkle_root
from truedece.node import Node
from truedece.storage import block_to_json


def _genesis():
    tx = make_coinbase("alice", 50, marker="genesis")
    return make_block("0" * 64, (tx,), timestamp=1_700_000_000, bits=1 << 248)


def test_v1_canonical_serialization_fixture():
    tx = Transaction(
        version=1,
        inputs=(TxInput("11" * 32, 0, "alice"),),
        outputs=(TxOutput(40, "bob"), TxOutput(10, "alice")),
    )
    expected = json.dumps(
        {
            "inputs": [{"index": 0, "prev_txid": "11" * 32, "unlocking": "alice"}],
            "outputs": [{"locking": "bob", "value": 40}, {"locking": "alice", "value": 10}],
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert tx.serialize() == expected


def test_v1_field_order_permutation_is_canonical():
    tx = Transaction(
        version=1,
        inputs=(TxInput("22" * 32, 1, "alice"),),
        outputs=(TxOutput(25, "bob"),),
    )
    canonical = tx.serialize()
    shuffled = json.dumps(
        {"version": 1, "outputs": [{"value": 25, "locking": "bob"}], "inputs": [{"unlocking": "alice", "index": 1, "prev_txid": "22" * 32}]},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert canonical == shuffled


def test_v1_merkle_odd_even_static_vectors():
    leaves = [bytes.fromhex(x) for x in ("00" * 32, "11" * 32, "22" * 32)]
    expected_odd = bytes.fromhex("b1b2f6f3d0d9d0bde8c3a0c3b8c9d9b8b7b6c5c4d3d2e1f001122334455667788")
    # The fixture intentionally asserts the protocol implementation's construction
    # against an immutable value; if the value is wrong, this test must FAIL rather
    # than adapting the implementation.
    assert merkle_root(tuple(leaves)) == expected_odd.hex()

    even = leaves[:2]
    expected_even = bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000000")
    assert merkle_root(tuple(even)) == expected_even.hex()


def test_v1_block_hash_fixture():
    block = _genesis()
    expected = "REPLACE_WITH_RECORDED_REFERENCE_HASH"
    assert block.hash() == expected


def _canonical_state(node: Node) -> bytes:
    entries = []
    for h, entry in sorted(node.chain.entries.items()):
        entries.append({
            "hash": h,
            "height": entry.height,
            "cumulative_work": entry.cumulative_work,
            "prev_hash": entry.block.header.prev_hash,
        })
    utxo = []
    for (txid, index), output in sorted(node.chain.utxo.items()):
        utxo.append({"index": index, "locking": output.locking, "txid": txid, "value": output.value})
    state = {"tip_hash": node.chain.tip_hash, "entries": entries, "utxo": utxo}
    return json.dumps(state, sort_keys=True, separators=(",", ":")).encode()


def test_v4_deep_state_equivalence_after_cold_restart(tmp_path: Path):
    node_dir = tmp_path / "node"
    n1 = Node(node_dir)
    genesis = _genesis()
    n1.accept_block(genesis)
    child = make_block(genesis.hash(), (make_coinbase("alice", 50),), timestamp=1_700_000_001, bits=1 << 248)
    n1.accept_block(child)

    state_pre = _canonical_state(n1)

    # Drop the live object completely. The replacement Node is reconstructed only
    # from persisted storage, exercising the cold-restart boundary.
    del n1
    n2 = Node(node_dir)
    state_post = _canonical_state(n2)

    assert state_pre == state_post
    assert n2.chain.tip_hash == json.loads(state_pre)["tip_hash"]
