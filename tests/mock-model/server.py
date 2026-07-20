#!/usr/bin/env python3
"""Minimal mock of the Anthropic Messages API for plugin *wiring* tests.

The wiring layer of tests/run-evals.sh points a real headless Claude Code
session at this server (ANTHROPIC_BASE_URL) and force-feeds it a scripted
sequence of tool calls — e.g. Bash("okteto up api"). The session's plugin
machinery is real: the PreToolUse guard hook, permission modes, and the Bash
tool all run exactly as they would against the live API. Only the model is
canned, which makes the tests deterministic and free (no API key).

Usage: server.py PLAYBOOK_JSON PORT_FILE

PLAYBOOK_JSON:
  {
    "sentinel": "WIRING-TEST",          // only answer conversations whose first
                                        // message contains this marker; other
                                        // requests (background haiku calls,
                                        // titles) get a bare "ok" reply
    "steps": [                          // steps[i] answers the request that
      [ {"type": "tool_use",            // carries i prior assistant messages,
         "name": "Bash",                // so retries are naturally idempotent
         "input": {"command": "okteto up api"}} ],
      [ {"type": "text", "text": "done"} ]
    ]
  }

Stdlib only; works on the macOS system python3 and GitHub Actions runners.
"""

import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def load_playbook(path):
    with open(path) as f:
        return json.load(f)


PLAYBOOK = load_playbook(sys.argv[1])
PORT_FILE = sys.argv[2] if len(sys.argv) > 2 else None


class Handler(BaseHTTPRequestHandler):
    # SSE bodies are EOF-terminated (Connection: close), so stay on HTTP/1.0
    # semantics and let each request use a fresh connection.
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):  # keep harness output clean
        sys.stderr.write("mock-model: %s\n" % (fmt % args))

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send_json(200, {"ok": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}

        path = self.path.split("?")[0].rstrip("/")
        if path.endswith("/count_tokens"):
            return self._send_json(200, {"input_tokens": 128})
        if not path.endswith("/messages"):
            return self._send_json(200, {"ok": True})

        messages = body.get("messages", [])
        sentinel = PLAYBOOK.get("sentinel")
        first_msg = json.dumps(messages[:1])
        if sentinel and sentinel not in first_msg:
            blocks = [{"type": "text", "text": "ok"}]
        else:
            step = sum(1 for m in messages if m.get("role") == "assistant")
            steps = PLAYBOOK.get("steps", [])
            if step < len(steps):
                blocks = steps[step]
            else:
                blocks = [{"type": "text", "text": "Playbook exhausted; stopping."}]

        blocks = [dict(b) for b in blocks]
        for b in blocks:
            if b.get("type") == "tool_use" and "id" not in b:
                b["id"] = "toolu_mock_" + uuid.uuid4().hex[:16]
        stop_reason = (
            "tool_use" if any(b.get("type") == "tool_use" for b in blocks) else "end_turn"
        )
        model = body.get("model", "mock-model")
        msg_id = "msg_mock_" + uuid.uuid4().hex[:16]

        if not body.get("stream"):
            return self._send_json(200, {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": blocks,
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 128, "output_tokens": 64},
            })

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        def event(name, data):
            self.wfile.write(
                ("event: %s\ndata: %s\n\n" % (name, json.dumps(data))).encode()
            )

        event("message_start", {
            "type": "message_start",
            "message": {
                "id": msg_id, "type": "message", "role": "assistant",
                "model": model, "content": [],
                "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 128, "output_tokens": 1},
            },
        })
        for i, b in enumerate(blocks):
            if b.get("type") == "tool_use":
                event("content_block_start", {
                    "type": "content_block_start", "index": i,
                    "content_block": {"type": "tool_use", "id": b["id"],
                                      "name": b["name"], "input": {}},
                })
                event("content_block_delta", {
                    "type": "content_block_delta", "index": i,
                    "delta": {"type": "input_json_delta",
                              "partial_json": json.dumps(b.get("input", {}))},
                })
            else:
                event("content_block_start", {
                    "type": "content_block_start", "index": i,
                    "content_block": {"type": "text", "text": ""},
                })
                event("content_block_delta", {
                    "type": "content_block_delta", "index": i,
                    "delta": {"type": "text_delta", "text": b.get("text", "")},
                })
            event("content_block_stop", {"type": "content_block_stop", "index": i})
        event("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 64},
        })
        event("message_stop", {"type": "message_stop"})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    if PORT_FILE:
        with open(PORT_FILE, "w") as f:
            f.write(str(port))
    print(port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
