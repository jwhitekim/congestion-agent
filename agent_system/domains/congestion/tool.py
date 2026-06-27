from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import cv2

from utils.base import BaseTool
from .models.tracker import ByteTrackAdapter
from .models.detector import YoloPredictor
from .models.result import build_track_result, build_segment_result


class TrackPeopleTool(BaseTool):
    """
    사람 탐지와 ByteTrack 추적을 묶은 사실 측정 도구.

    이 도구는 사람의 위치와 이동 궤적만 반환한다. 밀집도 점수, 혼잡도 레벨,
    action 같은 해석값은 만들지 않는다. 여기서 판단을 만들면 LLM(두뇌 역할)이 공간 분포를
    직접 해석할 수 없기 때문이다.
    """

    def __init__(self, model_path: str = "yolov8m.pt", default_sample_every_n: int = 5):
        self._model_path = model_path
        self._predictor: YoloPredictor | None = None  # LLM이 실제로 호출할 때만 로드
        self.default_sample_every_n = default_sample_every_n

    def _get_predictor(self) -> YoloPredictor:
        if self._predictor is None:
            self._predictor = YoloPredictor(self._model_path)
        return self._predictor

    @property
    def schema(self) -> dict:
        return {
            "name": "track_people",
            "description": (
                "Run YOLOv8m person detection and FoundationVision ByteTrack for a video segment. "
                "Returns only measured facts: track_id, bbox, center, frames_present, "
                "sampled_frames, and grid zone counts. Never returns density, congestion, or action labels."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "video_path": {"type": "string", "description": "Video file path."},
                    "start_sec": {"type": "number", "description": "Segment start time in seconds."},
                    "end_sec": {"type": "number", "description": "Segment end time in seconds."},
                    "sample_every_n": {"type": "integer", "description": "Track every N frames."},
                    "max_sampled_frames": {"type": "integer", "description": "Maximum sampled frames to process."},
                    "grid_rows": {"type": "integer", "description": "Rows for factual grid counts."},
                    "grid_cols": {"type": "integer", "description": "Columns for factual grid counts."},
                },
                "required": ["video_path"],
            },
        }

    def run(self, tool_input: dict) -> dict:
        video_path = Path(tool_input["video_path"])
        if not video_path.exists():
            raise RuntimeError(f"Video file not found: {video_path}")

        sample_every_n = max(1, int(tool_input.get("sample_every_n") or self.default_sample_every_n))
        max_sampled_frames = max(1, int(tool_input.get("max_sampled_frames") or 60))
        grid_rows = max(1, int(tool_input.get("grid_rows") or 3))
        grid_cols = max(1, int(tool_input.get("grid_cols") or 3))
        start_sec = tool_input.get("start_sec")
        end_sec = tool_input.get("end_sec")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if total_frames <= 0:
            cap.release()
            raise RuntimeError(f"Cannot read frame count: {video_path}")

        start_frame = int(float(start_sec) * fps) if start_sec is not None and fps else 0
        end_frame = int(float(end_sec) * fps) if end_sec is not None and fps else total_frames - 1
        start_frame = min(max(start_frame, 0), total_frames - 1)
        end_frame = min(max(end_frame, start_frame), total_frames - 1)

        tracks: dict[int, dict] = {}
        sampled_frames = []
        latest_positions = {}
        processed = 0
        tracker = ByteTrackAdapter(frame_rate=fps)

        try:
            frame_id = start_frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            while frame_id <= end_frame and processed < max_sampled_frames:
                ok, frame = cap.read()
                if not ok:
                    break

                if (frame_id - start_frame) % sample_every_n == 0:
                    timestamp = frame_id / fps if fps else None
                    detections = self._get_predictor().predict(frame, classes=[0], conf=0.1)
                    tracked = tracker.update(detections, image_shape=frame.shape[:2])
                    frame_people = []

                    for row in tracked:
                        values = row.tolist() if hasattr(row, "tolist") else list(row)
                        if len(values) < 5:
                            continue
                        x1, y1, x2, y2 = [round(float(value), 2) for value in values[:4]]
                        track_id = int(values[4])
                        center = [round((x1 + x2) / 2, 2), round((y1 + y2) / 2, 2)]
                        observation = {
                            "frame_index": frame_id,
                            "timestamp_sec": round(timestamp, 3) if timestamp is not None else None,
                            "bbox": [x1, y1, x2, y2],
                            "center": center,
                        }

                        if track_id not in tracks:
                            tracks[track_id] = {
                                "track_id": track_id,
                                "bbox": [x1, y1, x2, y2],
                                "center": center,
                                "frames_present": [],
                            }
                        tracks[track_id]["bbox"] = [x1, y1, x2, y2]
                        tracks[track_id]["center"] = center
                        tracks[track_id]["frames_present"].append(observation)
                        latest_positions[track_id] = center
                        frame_people.append({"track_id": track_id, "bbox": [x1, y1, x2, y2], "center": center})

                    sampled_frames.append({
                        "frame_index": frame_id,
                        "timestamp_sec": round(timestamp, 3) if timestamp is not None else None,
                        "people_count": len(frame_people),
                        "people": frame_people,
                    })
                    processed += 1

                frame_id += 1
        finally:
            cap.release()

        return build_track_result(
            video_path=video_path,
            segment=build_segment_result(start_sec, end_sec, start_frame, end_frame, fps),
            frame_size={"width": width, "height": height},
            sample_every_n=sample_every_n,
            sampled_frames=sampled_frames,
            tracks=tracks,
            zone_grid={"rows": grid_rows, "cols": grid_cols},
            zone_counts=self._build_zone_counts(latest_positions, width, height, grid_rows, grid_cols),
        )

    def _build_zone_counts(self, latest_positions, width: int, height: int, rows: int, cols: int) -> list[dict]:
        counts: defaultdict[tuple[int, int], int] = defaultdict(int)
        if width <= 0 or height <= 0:
            return []

        for center in latest_positions.values():
            cx, cy = center
            col = min(cols - 1, max(0, int(cx / width * cols)))
            row = min(rows - 1, max(0, int(cy / height * rows)))
            counts[(row, col)] += 1

        return [
            {
                "zone": f"r{row + 1}c{col + 1}",
                "row": row + 1,
                "col": col + 1,
                "people_count": counts[(row, col)],
            }
            for row in range(rows)
            for col in range(cols)
        ]
