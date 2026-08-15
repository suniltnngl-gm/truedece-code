# TrueDece

TrueDece is an independent Proof-of-Work protocol project focused on **true decentralization of a PoW ecosystem**.

## Current Milestone

### THIN-CORE-001 — Minimal PoW Blockchain

The first implementation milestone is a deliberately minimal executable control sample:

```text
Genesis
  ↓
Block
  ↓
PoW validation
  ↓
Transaction / UTXO transition
  ↓
Persistent storage
  ↓
Chain selection
  ↓
Minimal P2P propagation
  ↓
Independent-node convergence
```

The control sample must be deterministic, restartable, fork-capable, and independently reproducible.

## Core Boundary

- Block
- PoW
- Transactions / UTXO
- Storage
- Chain
- Minimal P2P
- Node
- Miner

## Explicitly Outside the Core

Multi-algorithm consensus, UTW/Ω/Λ, interlocking mechanisms, MMR/DA, L2/forced inclusion, DCM controls, Stratum V2, pool accounting, wallet abstraction, bridges, DEXs, and exchange integration.

## Repository Boundary

The private `truedece-research` repository is the authoritative research and control plane. This public repository is the executable implementation and reproducible evidence surface.

## Status

**THIN-CORE-001: ACTIVE — implementation starting from the frozen boundary.**