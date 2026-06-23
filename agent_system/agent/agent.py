# =============================================================================
# agent/agent.py  —  두뇌: ClaudeAgent
#
# 이 클래스는 도메인을 전혀 모른다.
# "영상 프레임을 보여주고 → 도구를 호출하고 → 결과를 수집하고 → 최종 판단을 받는다"는 흐름만 구현한다.
#
# 도메인(혼잡도, 행동인식, 화재감지 …)은 생성자 인자로 외부에서 주입된다.
# 도메인을 바꾸고 싶다면 이 파일은 건드리지 않아도 된다.
# =============================================================================

import base64
import json
import os
from pathlib import Path
from typing import List

import anthropic

from tools.base import BaseTool
from utils.custom_logger import GetLogger

logger = GetLogger("agent", "logs/agent.log")


# 짧은 별칭 → 실제 모델 ID
MODEL_ALIASES = {
    "opus":   "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5-20251001",
}
DEFAULT_MODEL = "opus"
DEFAULT_VISION_FRAMES = 8
MAX_FRAME_LONG_EDGE = 1280
JPEG_QUALITY = 80


def _load_cv2():
    try:
        import cv2
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "비디오 프레임 추출에는 opencv-python이 필요합니다. "
            "requirements.txt를 설치한 환경에서 실행하세요."
        ) from e
    return cv2


def _resize_for_vision(frame, max_long_edge: int = MAX_FRAME_LONG_EDGE):
    cv2 = _load_cv2()
    height, width = frame.shape[:2]
    long_edge = max(width, height)
    if long_edge <= max_long_edge:
        return frame

    scale = max_long_edge / long_edge
    resized_width = int(width * scale)
    resized_height = int(height * scale)
    return cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)


def _sample_video_frames(video_path: str, max_frames: int = DEFAULT_VISION_FRAMES) -> list[dict]:
    """
    Claude는 비디오 파일 경로를 직접 읽을 수 없으므로 대표 프레임을 이미지로 추출한다.
    반환값은 Claude Messages API의 image content block에 넣을 수 있는 JPEG base64 목록이다.
    """
    cv2 = _load_cv2()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"영상 파일을 열 수 없습니다: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            raise RuntimeError(f"프레임 수를 확인할 수 없습니다: {video_path}")

        frame_count = min(max_frames, total_frames)
        if frame_count == 1:
            target_indices = [0]
        else:
            target_indices = [
                round(i * (total_frames - 1) / (frame_count - 1))
                for i in range(frame_count)
            ]

        frames = []
        for index in target_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                logger.warning(f"프레임 추출 실패: index={index}")
                continue

            frame = _resize_for_vision(frame)
            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
            )
            if not ok:
                logger.warning(f"프레임 JPEG 인코딩 실패: index={index}")
                continue

            timestamp_sec = index / fps if fps else None
            frames.append({
                "index": index,
                "timestamp_sec": timestamp_sec,
                "data": base64.b64encode(encoded).decode("utf-8"),
            })

        if not frames:
            raise RuntimeError(f"Claude에 전달할 프레임을 추출하지 못했습니다: {video_path}")

        return frames
    finally:
        cap.release()


def _build_video_content(video_path: str) -> list[dict]:
    absolute_path = str(Path(video_path).resolve())
    sampled_frames = _sample_video_frames(absolute_path)

    content = [
        {
            "type": "text",
            "text": (
                "다음 영상을 분석하라. Claude가 직접 볼 수 있도록 "
                f"대표 프레임 {len(sampled_frames)}장을 함께 제공한다.\n"
                f"영상 파일 경로: {absolute_path}\n"
                "필요하면 등록된 도구를 호출해 보조 측정값을 얻고, "
                "최종 판단은 제공된 프레임의 시각 정보와 도구 결과를 종합해 내려라."
            ),
        }
    ]

    for number, frame in enumerate(sampled_frames, start=1):
        timestamp = frame["timestamp_sec"]
        if timestamp is None:
            frame_label = f"대표 프레임 {number} (원본 frame index: {frame['index']})"
        else:
            frame_label = (
                f"대표 프레임 {number} "
                f"(timestamp: {timestamp:.2f}s, 원본 frame index: {frame['index']})"
            )
        content.extend([
            {"type": "text", "text": frame_label},
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


class ClaudeAgent:
    """
    도메인 중립적인 에이전트 두뇌.

    ┌─────────────────────────────────────────────────────────┐
    │  두뇌의 단일 책임:                                        │
    │  1. 영상 대표 프레임을 Claude에 전달                       │
    │  2. Claude의 도구 호출 요청 → 실제 도구로 연결 (루프)      │
    │  3. Claude의 최종 JSON 판단을 파싱해 반환                 │
    │                                                         │
    │  두뇌가 모르는 것: 도메인, 도구의 구체적 동작, 출력 형식    │
    └─────────────────────────────────────────────────────────┘

    도메인 주입:
        ClaudeAgent(system_prompt="혼잡도 판단 지시문", tools=[CountPeopleTool()])
        → 동일한 두뇌를 어떤 도메인에도 재사용 가능.
    """

    def __init__(
        self,
        system_prompt: str,
        tools: List[BaseTool],
        model: str = DEFAULT_MODEL,
        output_schema: dict | None = None,
    ):
        # ── 두뇌 초기화 ────────────────────────────────────────────────────────
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.\n"
                "  Windows PowerShell : $env:ANTHROPIC_API_KEY = 'sk-ant-...'\n"
                "  Mac/Linux          : export ANTHROPIC_API_KEY=sk-ant-..."
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.output_schema = output_schema

        # ── 손발 등록 ──────────────────────────────────────────────────────────
        # 두뇌는 도구 이름으로만 도구를 찾는다. 구현 내용은 모른다.
        self.tools: List[BaseTool] = tools
        self._tool_map: dict[str, BaseTool] = {t.schema["name"]: t for t in tools}

    # ─────────────────────────────────────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────────────────────────────────────

    def _dispatch(self, tool_name: str, tool_input: dict) -> str:
        """
        Claude가 요청한 도구를 찾아 실행하고 JSON 문자열을 반환한다.

        두뇌는 도구가 무엇을 하는지 모른다.
        이름으로 찾아 run()을 호출할 뿐이다.
        """
        tool = self._tool_map.get(tool_name)
        if tool is None:
            return json.dumps({"error": f"등록되지 않은 도구: {tool_name}"})
        try:
            result = tool.run(tool_input)
            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": f"도구 실행 오류: {e}"})

    def _parse_json(self, text: str) -> dict:
        """Claude 텍스트 응답에서 JSON 객체를 추출·파싱한다."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        start, end = text.find("{"), text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(text[start:end])
        raise ValueError(f"JSON 파싱 실패:\n{text}")

    def _validate_output(self, result: dict) -> dict:
        """도메인이 제공한 최종 출력 계약을 검증한다."""
        if self.output_schema is None:
            return result
        if not isinstance(result, dict):
            raise ValueError("Claude 최종 응답은 JSON 객체여야 합니다.")

        required = self.output_schema.get("required", [])
        missing = [field for field in required if field not in result]
        if missing:
            raise ValueError(f"Claude 최종 응답에 필수 필드가 없습니다: {missing}")

        properties = self.output_schema.get("properties", {})
        for field, rules in properties.items():
            if field not in result:
                continue

            value = result[field]
            expected_type = rules.get("type")
            if expected_type == "string" and not isinstance(value, str):
                raise ValueError(f"'{field}' 필드는 문자열이어야 합니다: {value!r}")
            if expected_type == "number" and not isinstance(value, (int, float)):
                raise ValueError(f"'{field}' 필드는 숫자여야 합니다: {value!r}")

            allowed_values = rules.get("enum")
            if allowed_values is not None and value not in allowed_values:
                raise ValueError(
                    f"'{field}' 값이 허용 범위를 벗어났습니다: {value!r}. "
                    f"허용값: {allowed_values}"
                )

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # 핵심 메서드 — 두뇌의 전체 실행 흐름
    # ─────────────────────────────────────────────────────────────────────────

    def run(self, video_path: str) -> dict:
        """
        영상 파일 경로를 받아 최종 판단 JSON을 반환한다.

        흐름:
          [1] Claude에 영상 대표 프레임 + 영상 경로 + 도구 스키마 전달
          [2] tool_use 루프: 도구 호출 → 결과 반환 → 재호출 …
          [3] end_turn: 최종 JSON 파싱 후 반환
        """
        tool_schemas = [t.schema for t in self.tools]
        messages = [
            {
                "role": "user",
                "content": _build_video_content(video_path),
            }
        ]

        # ── [3] tool use 루프 ────────────────────────────────────────────────
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                tools=tool_schemas,
                messages=messages,
            )

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        logger.debug(f"도구 호출: {block.name}")
                        result_str = self._dispatch(block.name, block.input)
                        logger.debug(f"도구 결과: {json.loads(result_str)}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })

                messages.append({"role": "user", "content": tool_results})

            # ── [4] 최종 판단 ─────────────────────────────────────────────────
            elif response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text") and block.text.strip():
                        return self._validate_output(self._parse_json(block.text))
                raise ValueError("Claude 응답에 텍스트 블록이 없습니다.")

            else:
                raise ValueError(f"예상치 못한 stop_reason: {response.stop_reason}")
