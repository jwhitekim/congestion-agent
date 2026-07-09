import numpy as np
import supervision as sv
import torch


class Tracker:
    """ByteTrack 래퍼. track ID 안정화만 담당."""

    def __init__(self, frame_rate: float = 30.0):
        self._tracker = sv.ByteTrack(frame_rate=max(1, int(frame_rate or 30)))

    def update(self, detections: torch.Tensor) -> list:
        """
        Returns list of [x1, y1, x2, y2, track_id, score] arrays for confirmed tracks.
        Empty list when no detections.
        """
        if len(detections) == 0:
            return []

        det_array = detections.detach().cpu().numpy() if isinstance(detections, torch.Tensor) else np.asarray(detections)
        sv_dets = sv.Detections(xyxy=det_array[:, :4], confidence=det_array[:, 4])
        tracked = self._tracker.update_with_detections(sv_dets)

        rows = []
        for i in range(len(tracked)):
            x1, y1, x2, y2 = tracked.xyxy[i]
            track_id = int(tracked.tracker_id[i]) if tracked.tracker_id is not None else -1
            score = float(tracked.confidence[i]) if tracked.confidence is not None else 0.0
            rows.append([float(x1), float(y1), float(x2), float(y2), track_id, score])
        return rows
