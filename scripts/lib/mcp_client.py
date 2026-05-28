"""
Thin stdio JSON-RPC client for any MCP server.
Spawns the server as a subprocess, sends tool calls, returns results.
"""
import asyncio
import json
import subprocess
from typing import Any


class MCPClient:
    def __init__(self, command: list[str]):
        self.command = command
        self._proc: subprocess.Popen | None = None

    def start(self):
        self._proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def stop(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None

    def _send(self, payload: dict) -> dict:
        line = json.dumps(payload) + "\n"
        self._proc.stdin.write(line)
        self._proc.stdin.flush()
        response_line = self._proc.stdout.readline()
        return json.loads(response_line)

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        result = self._send(payload)
        if "error" in result:
            raise RuntimeError(f"MCP error: {result['error']}")
        return result.get("result", {}).get("content", result.get("result"))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
