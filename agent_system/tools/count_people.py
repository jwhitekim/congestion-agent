# =============================================================================
# tools/count_people.py  —  손발: YOLOv8 사람 카운팅 도구
#
# 두뇌가 "사람이 몇 명이야?"라고 물으면 이 도구가 정확한 숫자를 돌려준다.
# 판단(혼잡한지 여부)은 하지 않는다 — 그건 두뇌의 일이다.
# =============================================================================

import numpy as np
from ultralytics import YOLO

from .base import BaseTool
from utils.custom_logger import GetLogger

logger = GetLogger("tool", "logs/tool.log")


class CountPeopleTool(BaseTool):
    """YOLOv8m으로 프레임 내 사람 수를 카운팅하는 도구."""

    PERSON_CLASS_ID = 0  # COCO 데이터셋: class 0 = person

    def __init__(self, model_path: str = "yolov8m.pt"):
        logger.info("YOLOv8m 모델 로딩 중...")
        self.model = YOLO(model_path)
        self._frame: np.ndarray | None = None
        logger.info("YOLOv8m 준비 완료.")

    @property
    def schema(self) -> dict:
        return {
            "name": "count_people",
            "description": (
                "현재 분석 중인 프레임에서 YOLOv8m으로 사람 수를 정확히 카운팅합니다. "
                "장면에 몇 명이 있는지 알아야 할 때 반드시 이 도구를 먼저 호출하세요. "
                "반환값: {\"count\": 정수}"
            ),
            "input_schema": {
                "type": "object",
                # 현재 프레임은 에이전트가 prepare()로 자동 주입하므로 추가 인자 없음
                "properties": {},
                "required": [],
            },
        }

    def prepare(self, context: dict) -> None:
        """에이전트로부터 현재 프레임을 주입받는다."""
        self._frame = context.get("frame")

    def run(self, tool_input: dict) -> dict:
        if self._frame is None:
            raise RuntimeError("프레임이 주입되지 않았습니다. prepare()를 먼저 호출하세요.")

        results = self.model(self._frame, verbose=False)

        count = sum(
            1
            for result in results
            for box in result.boxes
            if int(box.cls) == self.PERSON_CLASS_ID
        )
        return {"count": count}
