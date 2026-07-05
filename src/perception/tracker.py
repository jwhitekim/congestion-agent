import torch
from ocsort import OCSort


class Tracker:
    """OC-SORT 래퍼. track ID 안정화만 담당."""

    def __init__(self, det_thresh: float = 0.3, max_age: int = 50, min_hits: int = 1):
        self._tracker = OCSort(det_thresh=det_thresh, max_age=max_age, min_hits=min_hits)

    def update(self, detections: torch.Tensor, frame_id: int) -> list:
        """
        Returns list of [x1, y1, x2, y2, track_id, ...] arrays for confirmed tracks.
        Empty list when no detections.
        """
        if len(detections) == 0:
            return []
        return self._tracker.update(detections, frame_id)
