import numpy as np
import torch
from ocsort.ocsort import OCSort


class Tracker:
    """OC-SORT 래퍼. track ID 안정화만 담당."""

    def __init__(self, frame_rate: float = 30.0, det_thresh: float = 0.3):
        # frame_rate는 OC-SORT가 안 쓰지만, pipeline.py 호출부(Tracker(frame_rate=fps))와
        # 인터페이스 호환을 위해 인자는 유지한다.
        #
        # det_thresh=0.3, max_age=50, min_hits=1: 원 캡스톤 레포
        # (jwhitekim/indoor-congestion-analysis,
        # backend/videostream/manager/video_processor.py 27번째 줄) 실측값 그대로 —
        # 원 논문에서 검증된 값이라 임의로 바꾸지 않는다.
        #
        # det_thresh=0.3은 config.py의 detector conf(0.07)보다 훨씬 높다. 이 둘은
        # 서로 다른 역할이다 — detector 단계(0.07)는 "일단 넓게 잡고", tracker
        # 단계(0.3)는 그중 무엇을 신뢰할지 다시 거른다. 정확히는: OCSort 기본값
        # use_byte=False라(이 호출에서도 켜지 않음) conf 0.07~0.3 사이 detection은
        # 새 트랙 생성뿐 아니라 기존 트랙 매칭에도 전혀 쓰이지 않고 그 프레임에서
        # 통째로 버려진다 — "새 트랙 시작만 못 한다"보다 더 강한 컷오프다.
        #
        # asso_func="ct_dist": 원 레포엔 명시돼 있지 않다(기본값 "iou"로 추정되나
        # 원 레포에서 직접 확인은 못 함) — head 박스가 작아 IoU 매칭이 구조적으로
        # 실패하는 문제(ByteTrack에서도 동일 현상 재현, scripts/diagnose_detector.py로
        # 검증) 때문에 우리 쪽 판단으로 유지한 것이다. 원 알고리즘 대비 변경한
        # 지점이므로 논문에 그렇게 밝혀야 한다. density 계산(perception/density.py의
        # calc_spatial_density, pipeline.py의 zone 계산)도 bbox 중심점만 쓰므로
        # 매칭 기준을 중심점으로 맞추는 것이 그 설계와 일관된 선택이기도 하다.
        self._tracker = OCSort(
            det_thresh=det_thresh, max_age=50, min_hits=1, asso_func="ct_dist", use_byte=True
        )

    def update(self, detections: torch.Tensor) -> list:
        """
        Returns list of [x1, y1, x2, y2, track_id, score] arrays for confirmed tracks.
        Empty list when no detections.
        OCSort.update()은 [x1,y1,x2,y2,conf,cls] 텐서를 그대로 받고
        (detector.py 출력 포맷과 동일, 변환 불필요),
        [x1,y1,x2,y2,track_id,cls,conf] 7열을 반환한다 — 여기서 track_id(4번 인덱스)와
        conf(6번 인덱스)만 뽑아 기존 6열 포맷([x1,y1,x2,y2,track_id,score])으로 맞춘다.
        """
        if len(detections) == 0:
            detections = torch.zeros((0, 6), dtype=torch.float32)

        tracked = self._tracker.update(detections, None)

        rows = []
        for row in tracked:
            x1, y1, x2, y2, track_id, cls, score = row
            rows.append([float(x1), float(y1), float(x2), float(y2), int(track_id), float(score)])
        return rows
