---
paths:
  - "src/trigger/**/*"
---

# trigger 레이어 세부 계약

`trigger/rules.py`는 매 세그먼트 `PerceptionResult` + `SegmentHistory`를 받아 rule로 트리거 여부를 판정한다.

**순간값이 아니라 변화율·지속시간 기반**이어야 한다(`density_delta_ratio`, `low_speed_streak_sec` 등) — 새 트리거 추가 시에도 이 기준을 지킬 것. **`hotspot`이 이 원칙의 유일한 예외**다(`zone_count > ZONE_MAX` 순간값만 보고 즉시 발동) — 새 코드가 이 패턴을 따라가지 않도록 주의. 의도적 예외로 유지할지 지속시간 조건을 추가할지는 미결정. `conflict` 트리거(`density_slope` 기반)는 원칙을 지킨다.

**우선순위/재호출 계약이 명시돼 있지 않다.** surge→stagnation→hotspot→conflict 순서로 검사해 처음 매칭되는 것 하나만 반환한다(두 조건이 동시에 참이어도 하나만 기록, 우선순위는 코드 순서가 암묵적으로 정함). cooldown/episode 상태가 없어서 같은 이상 상황이 지속되면 매 세그먼트 agent가 재호출된다. 이 동작을 바꾸려면 먼저 "트리거를 이벤트로 볼지 상태로 볼지"부터 정의할 것 — 새 트리거를 추가하며 이 계약을 암묵적으로 더 복잡하게 만들지 말 것.