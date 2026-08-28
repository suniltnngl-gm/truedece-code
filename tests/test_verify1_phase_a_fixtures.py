from __future__ import annotations

import json
from pathlib import Path

from truedece.core import (
    Block,
    BlockHeader,
    Transaction,
    TxInput,
    TxOutput,
    canonical_bytes,
    merkle_root,
)
from truedece.node import Node

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "verify1_phase_a_vectors.json"


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def tx_from_dict(data: dict) -> Transaction:
    return Transaction(
        version=data["version"],
        inputs=tuple(TxInput(**item) for item in data["inputs"]),
        outputs=tuple(TxOutput(**item) for item in data["outputs"]),
        coinbase=data["coinbase"],
    )


def header_from_dict(data: dict) -> BlockHeader:
    return BlockHeader(**data)


def canonical_state(node: Node) -> bytes:
    entries = []
    for block_hash, entry in sorted(node.chain.entries.items(), key=lambda item: item[1].height):
        entries.append(
            {
                "hash": block_hash,
                "height": entry.height,
                "cumulative_work": entry.cumulative_work,
                "prev_hash": entry.block.header.prev_hash,
            }
        )
    utxo = []
    for (txid, index), output in sorted(node.chain.utxo.items()):
        utxo.append(
            {
                "index": index,
                "locking": output.script_pubkey,
                "txid": txid,
                "value": output.value,
            }
        )
    state = {"tip_hash": node.chain.tip_hash, "entries": entries, "utxo": utxo}
    return canonical_bytes(state)


def test_v1_canonical_serialization_static_vector():
    f = fixture()["serialization"]["transaction"]
    tx = tx_from_dict(f["object"])
    assert tx.serialize() == bytes.fromhex(f["expected_bytes_hex"])
    assert len(tx.serialize()) == f["expected_length"]
    assert tx.txid() == f["expected_txid"]


def test_v1_field_permutation_invariance_static_vector():
    f = fixture()["serialization"]["permuted_transaction"]
    tx = tx_from_dict(f["canonical_object"])
    canonical = tx.serialize()
    shuffled = {
        "outputs": [{"script_pubkey": "bob", "value": 25}],
        "coinbase": False,
        "version": 1,
        "inputs": [
            {
                "script_sig": "alice",
                "prev_index": 1,
                "prev_txid": "22" * 32,
            }
        ],
    }
    assert canonical == bytes.fromhex(f["expected_bytes_hex"])
    assert canonical == canonical_bytes(shuffled)
    assert tx.txid() == f["expected_txid"]


def test_v1_merkle_static_vectors():
    f = fixture()["merkle"]
    leaves = f["leaves"]
    for count, expected in f["roots"].items():
        assert merkle_root(leaves[: int(count)]) == expected


def test_v1_block_header_static_vector():
    f = fixture()["block_header"]
    header = header_from_dict(f["fields"])
    assert header.serialize() == bytes.fromhex(f["expected_bytes_hex"])
    assert len(header.serialize()) == f["expected_length"]
    assert header.hash() == f["expected_hash"]


def test_v4_deep_state_static_vector_after_cold_restart(tmp_path: Path):
    f = fixture()["deep_state"]
    genesis = f["genesis"]
    child = f["child"]

    genesis_block = Block(
        header=header_from_dict(genesis["header"]),
        transactions=(tx_from_dict(genesis["transaction"]),),
    )
    child_block = Block(
        header=header_from_dict(child["header"]),
        transactions=(tx_from_dict(child["transaction"]),),
    )

    assert genesis_block.hash() == genesis["hash"]
    assert genesis_block.transactions[0].txid() == genesis["txid"]
    assert child_block.hash() == child["hash"]
    assert child_block.transactions[0].txid() == child["txid"]

    node_dir = tmp_path / "node"
    n1 = Node(node_dir)
    n1.accept_block(genesis_block)
    n1.accept_block(child_block)

    state_pre = canonical_state(n1)
    expected = f["state_pre_post"]
    assert state_pre == bytes.fromhex(expected["canonical_bytes_hex"])
    assert len(state_pre) == expected["length"]
    assert n1.chain.tip_hash == expected["json"]["tip_hash"]

    del n1
    n2 = Node(node_dir)
    state_post = canonical_state(n2)

    assert state_post == state_pre
    assert state_post == bytes.fromhex(expected["canonical_bytes_hex"])
    assert n2.chain.tip_hash == expected["json"]["tip_hash"]
    assert n2.chain.height == 1
    assert n2.chain.utxo == {(expected["json"]["utxo"][0]["txid"], 0): TxOutput(50, "alice")}
