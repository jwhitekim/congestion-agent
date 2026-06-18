# =============================================================================
# utils/video.py  —  동영상 유틸리티
# =============================================================================

import cv2
import numpy as np
from typing import Generator, Tuple

from utils.custom_logger import GetLogger

logger = GetLogger("video", "logs/video.log")


def sample_frames(
    video_path: str, interval_sec: int
) -> Generator[Tuple[np.ndarray, float], None, None]:
    """
    동영상에서 interval_sec 초 간격으로 프레임을 추출하는 제너레이터.

    Yields:
        (frame: np.ndarray, timestamp_sec: float)
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"동영상을 열 수 없습니다: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"동영상 정보: FPS={fps:.1f}, 총 {total}프레임, {total / fps:.1f}초")

    frame_step = max(1, int(fps * interval_sec))
    frame_idx = 0
    try:
        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            yield frame, frame_idx / fps
            frame_idx += frame_step
    finally:
        cap.release()
