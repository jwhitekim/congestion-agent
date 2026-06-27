
import cv2

MAX_FRAME_LONG_EDGE = 1280


def _resize_for_vision(frame, max_long_edge: int = MAX_FRAME_LONG_EDGE):
    height, width = frame.shape[:2]
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return frame
    scale = max_long_edge / long_edge
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    

def _split_timeline(duration_sec: float | None, interval_sec: float) -> list[dict]:
    if duration_sec is None:
        return [{"start_sec": 0.0, "end_sec": None}]

    segments = []
    start = 0.0
    while start < duration_sec:
        end = min(start + interval_sec, duration_sec)
        segments.append({"start_sec": round(start, 3), "end_sec": round(end, 3)})
        start = end
    return segments