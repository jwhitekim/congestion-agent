from __future__ import annotations
import cv2
import base64
from pathlib import Path

from utils.content import text_block, image_block

_MAX_FRAME_LONG_EDGE = 1280


def _resize_for_vision(frame, max_long_edge: int = _MAX_FRAME_LONG_EDGE):
    height, width = frame.shape[:2]
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return frame
    scale = max_long_edge / long_edge
    return cv2.resize(frame, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


class BaseVideoCapture:
    def __init__(self, video_path: str | Path):
        self.video_path = str(Path(video_path).resolve())
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {self.video_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    @property
    def video_metadata(self) -> dict:
        """비디오 메타데이터(fps, 총 프레임 수, 재생 시간)를 반환한다. main과 web 양쪽이 공유."""
        if self.total_frames <= 0:
            raise RuntimeError(f"Cannot read frame count: {self.video_path}")
        return {"fps": self.fps, "total_frames": self.total_frames, "duration_sec": self.total_frames / self.fps if self.fps else None}


class CustomCongestionVideoCapture(BaseVideoCapture):
    """비디오 캡처를 추상화한 클래스. cv2.VideoCapture를 래핑한다."""

    JPEG_QUALITY = 80

    def __init__(self, video_path: str | Path):
        super().__init__(video_path)
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cap.release()

    def _sample_frames(self, start_sec: float, end_sec: float | None, max_frames: int = 4) -> list[dict]:
        """구간에서 대표 프레임을 추출해 base64 인코딩된 dict 리스트로 반환한다."""
        start_frame = int(start_sec * self.fps) if self.fps else 0
        end_frame = int(end_sec * self.fps) if end_sec is not None and self.fps else self.total_frames - 1
        start_frame = min(max(start_frame, 0), self.total_frames - 1)
        end_frame = min(max(end_frame, start_frame), self.total_frames - 1)

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
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = self.cap.read()
            if not ok:
                continue
            frame = _resize_for_vision(frame)
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.JPEG_QUALITY])
            if not ok:
                continue
            frames.append({
                "index": index,
                "timestamp_sec": round(index / self.fps, 3) if self.fps else None,
                "data": base64.b64encode(encoded).decode("utf-8"),
            })

        if not frames:
            raise RuntimeError(f"No frames could be sampled: {self.video_path}")
        return frames

    def build_vision_content(self, start_sec: float, end_sec: float | None, max_frames: int = 4) -> list[dict]:
        """구간 메타데이터와 샘플 프레임을 Claude user content 리스트로 만든다. 도메인 중립."""
        frames = self._sample_frames(start_sec, end_sec, max_frames=max_frames)
        segment_label = f"{start_sec:.2f}s~{end_sec:.2f}s" if end_sec is not None else f"{start_sec:.2f}s~end"

        content: list[dict] = [
            text_block(
                f"video_path: {self.video_path}\n"
                f"segment: {segment_label}\n"
                f"start_sec: {start_sec}\n"
                f"end_sec: {end_sec}"
            )
        ]

        for number, frame in enumerate(frames, start=1):
            content.append(text_block(
                f"sample_frame {number}: "
                f"timestamp_sec={frame['timestamp_sec']}, frame_index={frame['index']}"
            ))
            content.append(image_block(frame["data"]))

        return content