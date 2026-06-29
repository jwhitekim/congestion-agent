"""
혼잡도 임계값 보정 스크립트.
동영상을 분석해 density 분포를 구하고 config.py의 DENSITY_LOW/HIGH 기준값을 제안한다.
결과는 프로젝트 루트의 calibration_thresholds.json에 저장된다.
"""

import json
import sys
from pathlib import Path

import cv2
import numpy as np

# 프로젝트 루트를 sys.path에 추가 (scripts/ 하위에서 실행할 때)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from perception.detector import Detector
from perception.density import calc_spatial_density
from perception.tracker import Tracker
import config

OUTPUT_FILE = ROOT / "calibration_thresholds.json"


def run_calibration(video_path: str, percentiles: tuple = (25, 50, 75)) -> None:
    print(f"[1단계] 임계값 보정 시작: {video_path}")

    detector = Detector()
    tracker = Tracker()
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"[오류] 동영상을 열 수 없습니다: {video_path}")
        return

    density_samples: list[float] = []
    frame_id = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_id += 1
        detections = detector.detect(frame)
        tracked = tracker.update(detections, frame_id)
        density = calc_spatial_density(tracked)

        if density > 0:
            density_samples.append(density)

        if frame_id % 30 == 0:
            print(f"   프레임 #{frame_id}  density={density:.1f}  샘플={len(density_samples)}")

    cap.release()
    print(f"\n... 처리 완료. 유효 샘플 {len(density_samples)}개 수집")

    if not density_samples:
        print("[오류] 수집된 데이터가 없습니다.")
        return

    arr = np.array(density_samples)
    thresholds = {
        f"p{p}": float(np.percentile(arr, p)) for p in percentiles
    }
    thresholds["suggested_DENSITY_LOW"] = thresholds[f"p{percentiles[0]}"]
    thresholds["suggested_DENSITY_HIGH"] = thresholds[f"p{percentiles[-1]}"]
    thresholds["sample_count"] = len(density_samples)
    thresholds["mean"] = float(arr.mean())
    thresholds["std"] = float(arr.std())

    OUTPUT_FILE.write_text(json.dumps(thresholds, indent=2))
    print(f"\n보정 완료 → {OUTPUT_FILE}")
    print(f"  suggested DENSITY_LOW  = {thresholds['suggested_DENSITY_LOW']:.2f}")
    print(f"  suggested DENSITY_HIGH = {thresholds['suggested_DENSITY_HIGH']:.2f}")
    print("  config.py에서 위 값을 업데이트하세요.")


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "samples" / "supermarket.mp4")
    run_calibration(video, percentiles=(25, 50, 75))
