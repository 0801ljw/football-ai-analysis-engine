"""Real child-process/HTTP checks; all data lives under pytest's temporary dir."""
import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "c" * 64


def start_child(tmp_path, port=0, token=TOKEN):
    env = {k: v for k, v in os.environ.items() if not k.startswith("WC_")}
    env.update(WC_DESKTOP_MODE="1", WC_APP_DATA_DIR=str(tmp_path), WC_HOST="127.0.0.1", PORT=str(port))
    child = subprocess.Popen([sys.executable, str(ROOT / "desktop/sidecar_main.py")],
                             cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    child.stdin.write((json.dumps({"token": token}) + "\n").encode())
    child.stdin.close()
    return child


def ready_port(child):
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(child.stdout.readline()), daemon=True).start()
    line = lines.get(timeout=15)
    assert TOKEN.encode() not in line
    return json.loads(line)["pitchmind_port"]


def stop(child):
    if child.poll() is None:
        child.terminate()
        try: child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)


def test_concurrent_children_hold_distinct_ports_and_authenticated_http(tmp_path):
    children = [start_child(tmp_path / str(n)) for n in range(2)]
    try:
        ports = [ready_port(child) for child in children]
        assert len(set(ports)) == 2
        for port in ports:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, transport=httpx.HTTPTransport(retries=10)) as client:
                assert client.get("/api/matches").status_code == 401
                assert client.get("/api/matches", headers={"X-Desktop-Session": "old-session"}).status_code == 401
                response = client.get("/api/system/doctor", headers={"X-Desktop-Session": TOKEN})
                assert response.status_code == 200
                assert TOKEN not in response.text
                assert client.get("/api/matches", headers={"X-Desktop-Session": TOKEN, "Host": "evil.example"}).status_code == 403
    finally:
        for child in children: stop(child)
    for child in children:
        assert TOKEN.encode() not in child.stderr.read()


def test_occupied_port_exits_without_announcing_ready(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        child = start_child(tmp_path, listener.getsockname()[1])
        try:
            assert child.wait(timeout=15) != 0
            assert child.stdout.read() == b""
            assert TOKEN.encode() not in child.stderr.read()
        finally: stop(child)


def test_invalid_bootstrap_fails_without_echo(tmp_path):
    child = start_child(tmp_path, token="short-invalid-test-token")
    try:
        assert child.wait(timeout=15) != 0
        assert child.stdout.read() == b""
        assert b"short-invalid-test-token" not in child.stderr.read()
    finally: stop(child)
