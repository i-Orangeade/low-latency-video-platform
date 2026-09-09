#!/usr/bin/env python3
"""Minimal end-to-end tests for all foundation labs."""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, capture_output=True)


def test_queue(executable: str) -> None:
    result = run_checked([executable, "3", "4", "5000", "7"])
    assert "validation=ok" in result.stdout, result.stdout


def test_echo(executable: str) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = subprocess.Popen(
        [executable, str(port), "32768"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                client = socket.create_connection(("127.0.0.1", port), timeout=1)
                break
            except OSError:
                if server.poll() is not None:
                    stdout, stderr = server.communicate()
                    raise AssertionError(
                        f"echo server exited early\nstdout={stdout}\nstderr={stderr}"
                    )
                if time.monotonic() >= deadline:
                    raise AssertionError("echo server did not start")
                time.sleep(0.02)

        payload = bytes(range(256)) * 2048
        with client:
            client.settimeout(5)
            client.sendall(payload)
            client.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        assert b"".join(chunks) == payload, "echo payload mismatch"
    finally:
        if server.poll() is None:
            server.send_signal(signal.SIGTERM)
        try:
            stdout, stderr = server.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            server.kill()
            stdout, stderr = server.communicate()
        assert server.returncode == 0, (
            f"echo server failed ({server.returncode})\n"
            f"stdout={stdout}\nstderr={stderr}"
        )


def flv_tag(tag_type: int, timestamp: int, payload: bytes) -> bytes:
    header = (
        bytes([tag_type])
        + len(payload).to_bytes(3, "big")
        + (timestamp & 0xFFFFFF).to_bytes(3, "big")
        + bytes([(timestamp >> 24) & 0xFF])
        + b"\x00\x00\x00"
    )
    return header + payload + struct.pack(">I", len(header) + len(payload))


def test_analyzer(analyzer: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        h264_path = root / "sample.h264"
        h264_path.write_bytes(
            b"\x00\x00\x00\x01\x67\x64\x00\x1f"
            b"\x00\x00\x01\x68\xee\x3c\x80"
            b"\x00\x00\x01\x65\x88\x84"
        )
        h264 = json.loads(
            run_checked(
                [sys.executable, analyzer, "--compact", str(h264_path)]
            ).stdout
        )
        assert h264["nal_units"] == 3
        assert h264["types"]["7"]["count"] == 1
        assert h264["types"]["8"]["count"] == 1
        assert h264["types"]["5"]["count"] == 1
        assert h264["forbidden_zero_bit_errors"] == 0

        flv_path = root / "sample.flv"
        flv_path.write_bytes(
            b"FLV\x01\x05\x00\x00\x00\x09"
            + b"\x00\x00\x00\x00"
            + flv_tag(18, 0, b"\x02\x00\x01x")
            + flv_tag(9, 40, b"\x17\x01\x00\x00\x00\x65")
            + flv_tag(8, 40, b"\xaf\x01\x11\x22")
        )
        flv = json.loads(
            run_checked(
                [sys.executable, analyzer, "--compact", str(flv_path)]
            ).stdout
        )
        assert flv["tag_count"] == 3
        assert flv["types"]["18"]["count"] == 1
        assert flv["types"]["9"]["bytes"] == 6
        assert flv["types"]["8"]["count"] == 1
        assert flv["timestamp_max_ms"] == 40
        assert flv["previous_tag_size_errors"] == 0
        assert flv["avc_packet_types"]["1"] == 1

        bad_path = root / "bad.flv"
        bad_path.write_bytes(b"FLV\x01")
        failure = subprocess.run(
            [sys.executable, analyzer, str(bad_path)],
            text=True,
            capture_output=True,
        )
        assert failure.returncode == 2
        assert "truncated FLV header" in failure.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--echo-server", required=True)
    parser.add_argument("--queue-demo", required=True)
    parser.add_argument("--analyzer", required=True)
    args = parser.parse_args()

    tests = [
        ("bounded queue", lambda: test_queue(args.queue_demo)),
        ("epoll echo", lambda: test_echo(args.echo_server)),
        ("media analyzer", lambda: test_analyzer(args.analyzer)),
    ]
    for name, test in tests:
        test()
        print(f"PASS: {name}")
    print(f"PASS: {len(tests)} foundation lab checks")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, subprocess.CalledProcessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
