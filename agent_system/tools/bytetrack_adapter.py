from __future__ import annotations

import numpy as np


class ByteTrackAdapter:
    """
    supervision.ByteTrack 어댑터.

    탐지 결과(x1,y1,x2,y2,conf,cls 형식)를 받아 ByteTrack으로 추적하고
    [x1,y1,x2,y2,track_id,score] 리스트를 돌려준다.
    판단(혼잡도, 밀집도)은 하지 않는다.
    """

    def __init__(self, frame_rate: float):
        try:
            import supervision as sv
        except ModuleNotFoundError as exc:
            raise RuntimeError("supervision is required: pip install supervision") from exc
        self._sv = sv
        self._tracker = sv.ByteTrack(frame_rate=max(1, int(frame_rate or 30)))

    def update(self, detections, image_shape: tuple[int, int]) -> list[list[float]]:
        det_array = self._to_numpy(detections)
        if det_array.shape[0] == 0:
            return []

        sv_dets = self._sv.Detections(
            xyxy=det_array[:, :4],
            confidence=det_array[:, 4],
        )
        tracked = self._tracker.update_with_detections(sv_dets)

        rows = []
        for i in range(len(tracked)):
            x1, y1, x2, y2 = tracked.xyxy[i]
            track_id = int(tracked.tracker_id[i]) if tracked.tracker_id is not None else -1
            score = float(tracked.confidence[i]) if tracked.confidence is not None else 0.0
            rows.append([float(x1), float(y1), float(x2), float(y2), track_id, score])
        return rows

    def _to_numpy(self, detections) -> np.ndarray:
        if detections is None:
            return np.empty((0, 5), dtype=float)
        if hasattr(detections, "detach"):
            detections = detections.detach().cpu().numpy()
        detections = np.asarray(detections, dtype=float)
        if detections.size == 0:
            return np.empty((0, 5), dtype=float)
        if detections.ndim == 1:
            detections = detections.reshape(1, -1)
        return detections[:, :5]
