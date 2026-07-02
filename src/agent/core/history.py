from collections import deque
from agent import config
from agent.types import PerceptionResult


class SegmentHistory:
    """
    직전 HISTORY_WINDOW 초의 PerceptionResult를 보관하는 링버퍼.
    변화율·추세 계산의 기준값을 제공한다.
    """

    def __init__(
        self,
        window_sec: float = config.HISTORY_WINDOW,
        interval_sec: float = config.SEGMENT_INTERVAL,
    ):
        max_len = max(1, int(window_sec / interval_sec))
        self._buffer: deque[PerceptionResult] = deque(maxlen=max_len)

    def add(self, result: PerceptionResult) -> None:
        self._buffer.append(result)

    def __len__(self) -> int:
        return len(self._buffer)

    def avg_density(self) -> float:
        if not self._buffer:
            return 0.0
        return sum(r.density for r in self._buffer) / len(self._buffer)

    def avg_speed(self) -> float:
        if not self._buffer:
            return 0.0
        return sum(r.avg_speed for r in self._buffer) / len(self._buffer)

    def speed_trend_with(self, current_speed: float) -> float:
        """
        버퍼 + current를 포함한 선형회귀 기울기.
        양수 = 가속 추세, 음수 = 감속 추세.
        """
        speeds = [r.avg_speed for r in self._buffer] + [current_speed]
        n = len(speeds)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(speeds) / n
        num = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(speeds))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den else 0.0

    def low_speed_streak_sec(self, speed_min: float, interval_sec: float) -> float:
        """버퍼 끝에서부터 연속으로 speed_min 미만이었던 누적 시간(초)."""
        streak = 0
        for r in reversed(self._buffer):
            if r.avg_speed < speed_min:
                streak += 1
            else:
                break
        return streak * interval_sec
