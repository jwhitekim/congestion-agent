from collections import deque


def calc_spatial_density(tracked_objects, scale: float = 1000) -> float:
    """
    Line Density: 인원 수 / 평균 쌍별 거리.
    analytics/occupancy.py의 calc_spatial_density와 동일 알고리즘.

    N<3(쌍별 거리 표본이 1개 이하)이면 0.0을 반환한다 — 원 논문 알고리즘 대비
    추가한 예외 처리다. 쌍별 거리가 정확히 하나뿐인 N=2는 통계적으로 평균/분산
    개념이 성립하지 않아, 두 사람이 화면상 우연히 가까우면 공식
    (len(centers) / avg_dist * scale)이 비정상적으로 폭발한다 (실측: t=325,
    2명, 12.8px → density=158.44, 다른 세그먼트 평균 20~40의 4~8배). N<2(0~1명)는
    이미 0.0을 반환해 왔으므로, 그 경계를 N<3까지 넓힌 것뿐이다.
    """
    centers = [
        ((obj[0] + obj[2]) / 2, (obj[1] + obj[3]) / 2)
        for obj in tracked_objects
    ]

    if len(centers) < 3:
        return 0.0

    total_dist = 0.0
    count = 0
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            dx = centers[i][0] - centers[j][0]
            dy = centers[i][1] - centers[j][1]
            total_dist += (dx * dx + dy * dy) ** 0.5
            count += 1

    avg_dist = total_dist / count
    return len(centers) / (avg_dist + 1e-6) * scale


def calc_avg_speed(track_trails: dict[int, deque], fps: float) -> float:
    """
    track_trails의 각 trail에서 프레임 간 이동 거리를 평균 → px/s.
    fps가 0이면 0.0 반환.
    """
    if fps <= 0:
        return 0.0

    speeds = []
    for trail in track_trails.values():
        pts = list(trail)
        if len(pts) < 2:
            continue
        dists = [
            ((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
            for i in range(len(pts) - 1)
        ]
        speeds.append(sum(dists) / len(dists) * fps)

    return sum(speeds) / len(speeds) if speeds else 0.0
