"""
TrackPeopleTool 출력 스키마 빌더.
도구(손발 역할)가 반환하는 사실(fact) 구조를 한 곳에서 정의한다.
구조가 바뀌면 여기만 수정한다.
"""


def build_track_result(
    video_path,
    segment: dict,
    frame_size: dict,
    sample_every_n: int,
    sampled_frames: list,
    tracks: dict,
    zone_grid: dict,
    zone_counts: list,
) -> dict:
    return {
        "video_path": str(video_path),
        "segment": segment,
        "frame_size": frame_size,
        "sample_every_n": sample_every_n,
        "sampled_frame_count": len(sampled_frames),
        "sampled_frames": sampled_frames,
        "people": sorted(tracks.values(), key=lambda item: item["track_id"]),
        "zone_grid": zone_grid,
        "zone_counts": zone_counts,
    }


def build_segment_result(start_sec, end_sec, start_frame: int, end_frame: int, fps: float) -> dict:
    return {
        "start_sec": float(start_sec) if start_sec is not None else 0.0,
        "end_sec": float(end_sec) if end_sec is not None else (round(end_frame / fps, 3) if fps else None),
        "start_frame": start_frame,
        "end_frame": end_frame,
    }
