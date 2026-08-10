from statistics import mean


def summarize_latency(samples_ms: list[float]) -> dict[str, float | int]:
    if not samples_ms:
        return {"count": 0, "avg_latency_ms": 0.0, "max_latency_ms": 0.0}

    return {
        "count": len(samples_ms),
        "avg_latency_ms": round(mean(samples_ms), 2),
        "max_latency_ms": round(max(samples_ms), 2),
    }
