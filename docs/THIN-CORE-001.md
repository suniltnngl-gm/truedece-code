# THIN-CORE-001 — Minimal PoW Blockchain

## Objective

Build the smallest runnable chain that demonstrates:

```text
Genesis → Block → PoW → Transaction/UTXO → Persistence → Chain Selection → P2P → Independent Convergence
```

## Frozen Interfaces

| Component | Responsibility |
|---|---|
| Block | Header + transactions |
| PoW | Target validation + work |
| Transactions | Deterministic validity + UTXO transition |
| Storage | Blocks/index/UTXO persistence |
| Chain | Parent linkage + cumulative work + fork handling |
| P2P | Handshake + block/transaction propagation |
| Node | Validation → storage → chain state |
| Miner | Template → nonce search → block |

## Acceptance

1. Same deterministic genesis on two independent nodes.
2. Valid PoW accepted; invalid PoW rejected.
3. Deterministic transaction validity and UTXO transition.
4. Persistent blocks, index, and UTXO state.
5. Cumulative-work chain selection with deterministic tie handling.
6. Two nodes converge on the same canonical tip.
7. Two nodes converge on the same UTXO state.
8. Deliberate fork resolves deterministically.
9. Stop/restart reconstructs the same tip, UTXO state, and chain work.

## Control-Sample Rule

This implementation is the baseline against which later protocol mechanisms are measured. Extension mechanisms are not dependencies of THIN-CORE-001.

The research/control repository maintains the authoritative specification and acceptance evidence.