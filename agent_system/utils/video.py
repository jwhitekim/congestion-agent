from __future__ import annotations

import base64
from pathlib import Path

MAX_FRAME_LONG_EDGE = 1280
JPEG_QUALITY = 80


def _load_cv2():
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("opencv-python is required to sample video frames.") from exc
    return cv2


def _resize_for_vision(frame, max_long_edge: int = MAX_FRAME_LONG_EDGE):
    cv2 = _load_cv2()
    height, width = frame.shape[:2]
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return frame
    scale = max_long_edge / long_edge
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def sample_frames(video_path: str, start_sec: float, end_sec: float | None, max_frames: int = 4) -> list[dict]:
    """구간에서 대표 프레임을 추출해 base64 인코딩된 dict 리스트로 반환한다."""
    cv2 = _load_cv2()
    path = str(Path(video_path).resolve())
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            raise RuntimeError(f"Cannot read frame count: {path}")

        start_frame = int(start_sec * fps) if fps else 0
        end_frame = int(end_sec * fps) if end_sec is not None and fps else total_frames - 1
        start_frame = min(max(start_frame, 0), total_frames - 1)
        end_frame = min(max(end_frame, start_frame), total_frames - 1)

        frame_count = min(max_frames, end_frame - start_frame + 1)
        if frame_count == 1:
            target_indices = [start_frame]
        else:
            target_indices = [
                round(start_frame + i * (end_frame - start_frame) / (frame_count - 1))
                for i in range(frame_count)
            ]

        frames = []
        for index in target_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                continue
            frame = _resize_for_vision(frame)
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ok:
                continue
            frames.append({
                "index": index,
                "timestamp_sec": round(index / fps, 3) if fps else None,
                "data": base64.b64encode(encoded).decode("utf-8"),
            })

        if not frames:
            raise RuntimeError(f"No frames could be sampled: {path}")
        return frames
    finally:
        cap.release()


def build_vision_content(video_path: str, start_sec: float, end_sec: float | None, max_frames: int = 4) -> list[dict]:
    """Claude API messages의 user content로 쓸 리스트를 만든다. LLM 층이 비디오를 몰라도 된다."""
    path = str(Path(video_path).resolve())
    frames = sample_frames(path, start_sec, end_sec, max_frames=max_frames)
    segment_label = f"{start_sec:.2f}s~{end_sec:.2f}s" if end_sec is not None else f"{start_sec:.2f}s~end"

    content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Analyze this video segment.\n"
                f"video_path: {path}\n"
                f"segment: {segment_label}\n"
                f"start_sec: {start_sec}\n"
                f"end_sec: {end_sec}\n\n"
                "먼저 제공된 프레임을 직접 보고 판단하라. "
                "사람 위치/이동/구역별 분포 사실이 더 필요하다고 스스로 판단되면 "
                "track_people 도구를 호출하라. 도구를 호출할 때는 위 video_path, "
                "start_sec, end_sec 값을 사용하라."
            ),
        }
    ]

    for number, frame in enumerate(frames, start=1):
        content.extend([
            {
                "type": "text",
                "text": (
                    f"sample_frame {number}: "
                    f"timestamp_sec={frame['timestamp_sec']}, frame_index={frame['index']}"
                ),
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": frame["data"],
                },
            },
        ])

    return content
