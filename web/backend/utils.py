def _build_segments(duration_sec: float | None, interval_sec: float) -> list[dict]:
    if duration_sec is None:
        return [{"start_sec": 0.0, "end_sec": None}]

    segments = []
    start = 0.0
    while start < duration_sec:
        end = min(start + interval_sec, duration_sec)
        segments.append({"start_sec": round(start, 3), "end_sec": round(end, 3)})
        start = end
    return segments
