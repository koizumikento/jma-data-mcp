"""Fail when the bundled AMeDAS station snapshot differs from JMA."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import urlopen

SOURCE_URL = "https://www.jma.go.jp/bosai/amedas/const/amedastable.json"
SNAPSHOT = Path(__file__).parents[1] / "jma_data_mcp" / "data" / "amedas_stations.json"


def main() -> int:
    local = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    with urlopen(SOURCE_URL, timeout=30) as response:  # noqa: S310 - fixed JMA URL
        upstream = json.load(response)

    differences: list[str] = []
    local_codes, upstream_codes = set(local), set(upstream)
    for code in sorted(local_codes - upstream_codes):
        differences.append(f"removed upstream: {code}")
    for code in sorted(upstream_codes - local_codes):
        differences.append(f"added upstream: {code}")

    for code in sorted(local_codes & upstream_codes):
        station = local[code]
        source = upstream[code]
        expected = {
            "type": source["type"],
            "elements": source["elems"],
            "name": {
                "ja": source["kjName"],
                "kana": source["knName"],
                "en": source["enName"],
            },
            "location": {
                "lat": round(source["lat"][0] + source["lat"][1] / 60, 6),
                "lon": round(source["lon"][0] + source["lon"][1] / 60, 6),
                "lat_dm": source["lat"],
                "lon_dm": source["lon"],
                "alt": source["alt"],
            },
        }
        actual = {key: station[key] for key in expected}
        if actual != expected:
            differences.append(f"changed upstream: {code}")

    if differences:
        print("AMeDAS snapshot drift detected:", *differences[:20], sep="\n- ")
        return 1
    print(f"AMeDAS snapshot is current: {len(local)} stations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
