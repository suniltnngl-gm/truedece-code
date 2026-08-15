from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Awaitable, Callable

from .node import Node
from .storage import block_from_json, block_to_json


@dataclass
class Peer:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter

    async def send(self, message: dict) -> None:
        self.writer.write((json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n").encode())
        await self.writer.drain()


class P2PNode:
    """Minimal line-delimited TCP transport around the Node consensus boundary."""

    def __init__(self, node: Node, protocol_version: int = 1) -> None:
        self.node = node
        self.protocol_version = protocol_version
        self.peers: set[Peer] = set()
        self.server: asyncio.AbstractServer | None = None

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self.server = await asyncio.start_server(self._handle_connection, host, port)
        return self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        for peer in list(self.peers):
            peer.writer.close()
            await peer.writer.wait_closed()
        self.peers.clear()

    async def connect(self, host: str, port: int) -> None:
        reader, writer = await asyncio.open_connection(host, port)
        peer = Peer(reader, writer)
        await peer.send({"type": "handshake", "version": self.protocol_version})
        self.peers.add(peer)
        asyncio.create_task(self._read_peer(peer))

    async def broadcast_block(self, block) -> None:
        message = {"type": "block", "block": block_to_json(block)}
        await asyncio.gather(*(peer.send(message) for peer in list(self.peers)), return_exceptions=True)

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = Peer(reader, writer)
        self.peers.add(peer)
        try:
            await peer.send({"type": "handshake", "version": self.protocol_version})
            await self._read_peer(peer)
        finally:
            self.peers.discard(peer)
            writer.close()
            await writer.wait_closed()

    async def _read_peer(self, peer: Peer) -> None:
        while True:
            line = await peer.reader.readline()
            if not line:
                return
            message = json.loads(line.decode())
            kind = message.get("type")
            if kind == "handshake":
                if message.get("version") != self.protocol_version:
                    return
            elif kind == "block":
                block = block_from_json(message["block"])
                self.node.accept_block(block)
            elif kind == "transaction":
                # Transaction transport is deliberately surfaced but transaction
                # admission/mempool policy remains outside this first network slice.
                continue
