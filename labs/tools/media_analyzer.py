#!/usr/bin/env python3
"""Inspect Annex-B H.264 elementary streams and FLV tag headers."""

from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys
from collections import Counter
from typing import Any, Iterator


NAL_NAMES = {
    1: "non_idr_slice",
    5: "idr_slice",
    6: "sei",
    7: "sps",
    8: "pps",
    9: "access_unit_delimiter",
}
FLV_TAG_NAMES = {8: "audio", 9: "video", 18: "script"}


class ParseError(ValueError):
    """Raised when an input is structurally invalid or truncated."""


def _start_codes(data: bytes) -> list[tuple[int, int]]:
    starts: list[tuple[int, int]] = []
    index = 0
    while index + 3 <= len(data):
        if data[index : index + 3] == b"\x00\x00\x01":
            starts.append((index, 3))
            index += 3
        elif (
            index + 4 <= len(data)
            and data[index : index + 4] == b"\x00\x00\x00\x01"
        ):
            starts.append((index, 4))
            index += 4
        else:
            index += 1
    return starts


def annexb_nals(data: bytes) -> Iterator[tuple[int, bytes]]:
    starts = _start_codes(data)
    if not starts:
        raise ParseError("no Annex-B start code found")
    if any(data[: starts[0][0]]):
        raise ParseError("non-zero bytes precede first Annex-B start code")

    for number, (offset, prefix_size) in enumerate(starts):
        payload_start = offset + prefix_size
        payload_end = starts[number + 1][0] if number + 1 < len(starts) else len(data)
        payload = data[payload_start:payload_end].rstrip(b"\x00")
        if not payload:
            raise ParseError(f"empty NAL unit at byte offset {offset}")
        yield offset, payload


def analyze_h264(data: bytes) -> dict[str, Any]:
    nals = list(annexb_nals(data))
    type_counts = Counter(payload[0] & 0x1F for _, payload in nals)
    forbidden_zero_bit_errors = sum(bool(payload[0] & 0x80) for _, payload in nals)
    return {
        "format": "annexb-h264",
        "input_bytes": len(data),
        "nal_units": len(nals),
        "nal_payload_bytes": sum(len(payload) for _, payload in nals),
        "forbidden_zero_bit_errors": forbidden_zero_bit_errors,
        "types": {
            str(nal_type): {
                "name": NAL_NAMES.get(nal_type, "other"),
                "count": type_counts[nal_type],
                "bytes": sum(
                    len(payload)
                    for _, payload in nals
                    if payload[0] & 0x1F == nal_type
                ),
            }
            for nal_type in sorted(type_counts)
        },
        "units": [
            {
                "offset": offset,
                "type": payload[0] & 0x1F,
                "name": NAL_NAMES.get(payload[0] & 0x1F, "other"),
                "nal_ref_idc": (payload[0] >> 5) & 0x03,
                "bytes": len(payload),
            }
            for offset, payload in nals
        ],
    }


def _u24(data: bytes) -> int:
    return int.from_bytes(data, "big")


def analyze_flv(data: bytes) -> dict[str, Any]:
    if len(data) < 13:
        raise ParseError("truncated FLV header")
    if data[:3] != b"FLV":
        raise ParseError("invalid FLV signature")

    version = data[3]
    flags = data[4]
    data_offset = struct.unpack(">I", data[5:9])[0]
    if data_offset < 9 or data_offset + 4 > len(data):
        raise ParseError("invalid FLV data offset")
    initial_previous_size = struct.unpack(">I", data[data_offset : data_offset + 4])[0]
    if initial_previous_size != 0:
        raise ParseError("first PreviousTagSize must be zero")

    position = data_offset + 4
    tags: list[dict[str, Any]] = []
    type_counts: Counter[int] = Counter()
    type_bytes: Counter[int] = Counter()
    timestamp_min: int | None = None
    timestamp_max: int | None = None
    previous_size_errors = 0
    avc_packet_counts: Counter[int] = Counter()

    while position < len(data):
        if len(data) - position < 11:
            raise ParseError(f"truncated FLV tag header at byte offset {position}")
        tag_offset = position
        tag_type = data[position] & 0x1F
        filtered = bool(data[position] & 0x20)
        data_size = _u24(data[position + 1 : position + 4])
        timestamp = _u24(data[position + 4 : position + 7]) | (
            data[position + 7] << 24
        )
        stream_id = _u24(data[position + 8 : position + 11])
        payload_start = position + 11
        payload_end = payload_start + data_size
        if payload_end + 4 > len(data):
            raise ParseError(f"truncated FLV tag payload at byte offset {tag_offset}")

        previous_size = struct.unpack(">I", data[payload_end : payload_end + 4])[0]
        expected_previous_size = 11 + data_size
        if previous_size != expected_previous_size:
            previous_size_errors += 1

        type_counts[tag_type] += 1
        type_bytes[tag_type] += data_size
        timestamp_min = timestamp if timestamp_min is None else min(timestamp_min, timestamp)
        timestamp_max = timestamp if timestamp_max is None else max(timestamp_max, timestamp)

        tag: dict[str, Any] = {
            "offset": tag_offset,
            "type": tag_type,
            "name": FLV_TAG_NAMES.get(tag_type, "unknown"),
            "data_size": data_size,
            "timestamp_ms": timestamp,
            "stream_id": stream_id,
            "filtered": filtered,
            "previous_tag_size": previous_size,
            "previous_tag_size_valid": previous_size == expected_previous_size,
        }
        if tag_type == 9 and data_size >= 2:
            payload = data[payload_start:payload_end]
            codec_id = payload[0] & 0x0F
            tag["frame_type"] = payload[0] >> 4
            tag["codec_id"] = codec_id
            if codec_id == 7:
                avc_packet_type = payload[1]
                tag["avc_packet_type"] = avc_packet_type
                avc_packet_counts[avc_packet_type] += 1
        tags.append(tag)
        position = payload_end + 4

    return {
        "format": "flv",
        "input_bytes": len(data),
        "version": version,
        "has_audio": bool(flags & 0x04),
        "has_video": bool(flags & 0x01),
        "header_size": data_offset,
        "tag_count": len(tags),
        "tag_payload_bytes": sum(type_bytes.values()),
        "timestamp_min_ms": timestamp_min,
        "timestamp_max_ms": timestamp_max,
        "previous_tag_size_errors": previous_size_errors,
        "types": {
            str(tag_type): {
                "name": FLV_TAG_NAMES.get(tag_type, "unknown"),
                "count": type_counts[tag_type],
                "bytes": type_bytes[tag_type],
            }
            for tag_type in sorted(type_counts)
        },
        "avc_packet_types": {
            str(packet_type): count
            for packet_type, count in sorted(avc_packet_counts.items())
        },
        "tags": tags,
    }


def detect_format(data: bytes) -> str:
    if data.startswith(b"FLV"):
        return "flv"
    if _start_codes(data):
        return "h264"
    raise ParseError("cannot detect input format; use --format")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("--format", choices=("auto", "h264", "flv"), default="auto")
    parser.add_argument("--compact", action="store_true", help="emit one-line JSON")
    args = parser.parse_args()

    try:
        data = args.input.read_bytes()
        input_format = detect_format(data) if args.format == "auto" else args.format
        result = analyze_h264(data) if input_format == "h264" else analyze_flv(data)
        result["path"] = str(args.input)
        print(
            json.dumps(
                result,
                ensure_ascii=False,
                sort_keys=True,
                indent=None if args.compact else 2,
            )
        )
        return 0
    except (OSError, ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
