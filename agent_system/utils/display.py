def print_result(record: dict) -> None:
    segment = record.get("segment", {})
    prefix = f"[segment {record.get('segment_index', '?')}: {segment.get('start_sec')}~{segment.get('end_sec')}s]"

    if "error" in record:
        print(f"{prefix} ERROR: {record['error']}")
        return

    result = record.get("result", record)
    print(prefix)
    print(f"  total_people        : {result.get('total_people', '?')}")
    print(f"  congestion_level    : {result.get('congestion_level', '?')}")
    print(f"  action              : {result.get('action', '?')}")
    print(f"  local_hotspots      : {result.get('local_hotspots', [])}")
    print(f"  distribution_summary: {result.get('distribution_summary', '')}")
    print(f"  reasoning           : {result.get('reasoning', '')}")
