import asyncio

from truedece.core import make_block, make_coinbase
from truedece.node import Node
from truedece.p2p import P2PNode

TARGET = 1 << 248


def genesis():
    return make_block("0" * 64, (make_coinbase("genesis", 50),), timestamp=1_700_000_000, bits=TARGET)


def test_two_nodes_propagate_and_converge(tmp_path):
    async def scenario():
        g = genesis()
        node_a = Node(tmp_path / "a")
        node_b = Node(tmp_path / "b")
        node_a.accept_block(g)
        node_b.accept_block(g)

        net_a = P2PNode(node_a)
        net_b = P2PNode(node_b)
        port = await net_b.start()
        await net_a.connect("127.0.0.1", port)

        block = make_block(g.hash(), (make_coinbase("alice", 50),), timestamp=1_700_000_001, bits=TARGET)
        node_a.accept_block(block)
        await net_a.broadcast_block(block)
        await asyncio.sleep(0.05)

        assert node_a.chain.tip_hash == node_b.chain.tip_hash
        assert node_a.chain.utxo == node_b.chain.utxo
        await net_a.stop()
        await net_b.stop()

    asyncio.run(scenario())


def test_two_nodes_resolve_equal_work_fork(tmp_path):
    async def scenario():
        g = genesis()
        node_a = Node(tmp_path / "a")
        node_b = Node(tmp_path / "b")
        node_a.accept_block(g)
        node_b.accept_block(g)

        net_a = P2PNode(node_a)
        net_b = P2PNode(node_b)
        port_a = await net_a.start()
        port_b = await net_b.start()
        await net_a.connect("127.0.0.1", port_b)
        await net_b.connect("127.0.0.1", port_a)

        fork_a = make_block(g.hash(), (make_coinbase("alice", 50),), timestamp=1_700_000_001, bits=TARGET)
        fork_b = make_block(g.hash(), (make_coinbase("bob", 50),), timestamp=1_700_000_002, bits=TARGET)
        node_a.accept_block(fork_a)
        node_b.accept_block(fork_b)
        await net_a.broadcast_block(fork_a)
        await net_b.broadcast_block(fork_b)
        await asyncio.sleep(0.05)

        expected = min(fork_a.hash(), fork_b.hash())
        assert node_a.chain.tip_hash == expected
        assert node_b.chain.tip_hash == expected
        await net_a.stop()
        await net_b.stop()

    asyncio.run(scenario())
