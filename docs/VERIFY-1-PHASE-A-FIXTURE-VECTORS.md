# VERIFY-1 Phase A — Required Fixture Vectors

This is the required fixture inventory. It intentionally contains no expected values until those values are independently recorded.

## V1.1 Serialization
- TX-CANON-001: canonical transaction bytes
- BLOCK-CANON-001: canonical block bytes
- permutation variants must equal the same recorded bytes

## V1.2 Transaction ID
- TX-HASH-001: transaction canonical bytes + expected txid

## V1.3 Merkle
- MERKLE-001: one leaf
- MERKLE-002: two leaves
- MERKLE-003: three leaves / odd duplication
- MERKLE-004: four leaves

## V1.4 Block hash
- BLOCK-HASH-001: complete header fields + serialized header + expected hash

## V4 persistence
- STATE-001: genesis + child pre-shutdown canonical state
- STATE-001-RESTART: independently reconstructed state must equal STATE-001 byte-for-byte

Expected values are to be recorded independently and then frozen. No test may calculate its expected fixture from the implementation under test.
