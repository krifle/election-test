#!/usr/bin/env python3
"""관내사전투표와 선거일투표의 쌍둥이 득표 빈도를 비교한다."""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

YEARS = (2014, 2018, 2022)
CHANNELS = ("in_person_advance", "election_day")
SPECIAL_SUBSTRINGS = ("잘못 투입·구분된 투표지",)
N_BINS = (
    (0, 499),
    (500, 999),
    (1000, 1999),
    (2000, 3999),
    (4000, 999999),
)


def load_units(year: int, channel: str) -> list[dict[str, object]]:
    path = Path(f"data/historical/kr-local-{year}-{channel}.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    units = []
    for unit in payload["units"]:
        if any(token in unit["unit_name"] for token in SPECIAL_SUBSTRINGS):
            continue
        unit = dict(unit)
        unit["year"] = year
        unit["channel"] = channel
        unit["top2_signature"] = top2_signature(unit)
        units.append(unit)
    return units


def top2_signature(unit: dict[str, object]) -> tuple[int, int] | None:
    votes = sorted((candidate["votes"] for candidate in unit["candidates"]), reverse=True)
    if len(votes) < 2 or votes[1] <= 0:
        return None
    return votes[0], votes[1]


def n_bin(total_valid_votes: int) -> str:
    for lower, upper in N_BINS:
        if lower <= total_valid_votes <= upper:
            return f"{lower}-{upper}"
    raise ValueError(total_valid_votes)


def pair_count(count: int) -> int:
    return count * (count - 1) // 2


def summarize_units(units: list[dict[str, object]]) -> dict[str, object]:
    totals = [int(unit["total_valid_votes"]) for unit in units if unit["top2_signature"] is not None]
    return {
        "unit_count": len(units),
        "comparable_unit_count": len(totals),
        "median_total_valid_votes": statistics.median(totals),
        "mean_total_valid_votes": round(statistics.mean(totals), 2),
    }


def summarize_top2_pairs(units: list[dict[str, object]]) -> dict[str, object]:
    by_contest: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_signature: dict[tuple[str, tuple[int, int]], list[dict[str, object]]] = defaultdict(list)

    for unit in units:
        signature = unit["top2_signature"]
        if signature is None:
            continue
        contest_id = str(unit["contest_id"])
        by_contest[contest_id].append(unit)
        by_signature[(contest_id, signature)].append(unit)

    all_pairs = sum(pair_count(len(group)) for group in by_contest.values())
    match_pairs = sum(pair_count(len(group)) for group in by_signature.values())
    return {
        "all_pairs": all_pairs,
        "matching_pairs": match_pairs,
        "matching_pair_rate": match_pairs / all_pairs if all_pairs else 0.0,
    }


def summarize_by_n_bin(units: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    binned_units: dict[str, list[dict[str, object]]] = defaultdict(list)
    for unit in units:
        signature = unit["top2_signature"]
        if signature is None:
            continue
        binned_units[n_bin(int(unit["total_valid_votes"]))].append(unit)

    summary: dict[str, dict[str, object]] = {}
    for bin_name, group in binned_units.items():
        bin_pairs = summarize_top2_pairs(group)
        summary[bin_name] = {
            "unit_count": len(group),
            "matching_pairs": bin_pairs["matching_pairs"],
            "all_pairs": bin_pairs["all_pairs"],
            "matching_pair_rate": bin_pairs["matching_pair_rate"],
        }
    return dict(sorted(summary.items()))


def summarize_examples(units: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, tuple[int, int]], list[dict[str, object]]] = defaultdict(list)
    for unit in units:
        signature = unit["top2_signature"]
        if signature is None:
            continue
        groups[(str(unit["contest_id"]), signature)].append(unit)

    rows = []
    for (contest_id, signature), group in groups.items():
        if len(group) < 2:
            continue
        rows.append(
            {
                "contest_id": contest_id,
                "signature": list(signature),
                "pair_count": pair_count(len(group)),
                "unit_count": len(group),
                "units": [unit["unit_name"] for unit in group[:8]],
            }
        )
    rows.sort(key=lambda item: (-item["pair_count"], item["contest_id"], item["signature"]))
    return rows[:12]


def build_report() -> dict[str, object]:
    report: dict[str, object] = {"years": {}}
    aggregate_by_channel: dict[str, list[dict[str, object]]] = defaultdict(list)

    for year in YEARS:
        report["years"][str(year)] = {}
        for channel in CHANNELS:
            units = load_units(year, channel)
            aggregate_by_channel[channel].extend(units)
            report["years"][str(year)][channel] = {
                "units": summarize_units(units),
                "top2_pairs": summarize_top2_pairs(units),
                "top2_pairs_by_n_bin": summarize_by_n_bin(units),
                "top2_examples": summarize_examples(units),
            }

    report["aggregate"] = {}
    for channel in CHANNELS:
        units = aggregate_by_channel[channel]
        report["aggregate"][channel] = {
            "units": summarize_units(units),
            "top2_pairs": summarize_top2_pairs(units),
            "top2_pairs_by_n_bin": summarize_by_n_bin(units),
            "top2_examples": summarize_examples(units),
        }
    return report


def main() -> None:
    report = build_report()
    output_path = Path("results/historical/advance-vs-election-day.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON 저장: {output_path}")


if __name__ == "__main__":
    main()
