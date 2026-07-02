"""
영상 파일 → (timestamp, frame) 프레임 스트림.
모든 프레임을 순서대로 내보낸다.
perception/pipeline.py가 SEGMENT_INTERVAL 단위로 집계를 담당한다.
"""

from typing import Generator, Tuple
import cv2
import numpy as np


def get_video_fps(video_path: str) -> float:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    return fps


def iter_frames(video_path: str) -> Generator[Tuple[float, np.ndarray], None, None]:
    """
    Yields (timestamp_sec, frame) for every frame in the video.
    Releases the capture on exhaustion or error.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield frame_idx / fps, frame
            frame_idx += 1
    finally:
        cap.release()
