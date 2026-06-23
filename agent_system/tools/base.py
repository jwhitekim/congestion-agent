# =============================================================================
# tools/base.py  —  모든 도구의 공통 인터페이스
#
# ClaudeAgent(판단 본체)는 이 클래스만 안다.
# 구체적인 도구(YOLO, 날씨 API 등)가 무엇인지 ClaudeAgent는 신경 쓰지 않는다.
#
# 새 도구 추가 방법:
#   1. 이 클래스를 상속
#   2. schema 프로퍼티와 run() 메서드를 구현
#   3. 이미지 등 외부 컨텍스트가 필요하면 prepare()도 오버라이드
# =============================================================================

from abc import ABC, abstractmethod


class BaseTool(ABC):
    """에이전트 시스템 도구의 공통 기반 클래스."""

    @property
    @abstractmethod
    def schema(self) -> dict:
        """
        Claude tool use 스키마를 반환한다.
        필수 필드: name, description, input_schema
        """
        ...

    def prepare(self, context: dict) -> None:
        """
        run() 호출 직전에 ClaudeAgent(판단 본체)로부터 컨텍스트를 주입받는다.

        이미지 처리 도구 → context["frame"] 저장
        외부 API 도구    → 별도 컨텍스트 키 사용
        컨텍스트 불필요  → 오버라이드 생략 (기본: no-op)
        """
        pass

    @abstractmethod
    def run(self, tool_input: dict) -> dict:
        """
        실제 도구 로직을 실행한다.
        tool_input: Claude가 schema.input_schema에 맞춰 전달한 인자.
        반환: JSON 직렬화 가능한 dict.
        """
        ...
