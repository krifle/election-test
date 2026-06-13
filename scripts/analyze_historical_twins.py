#!/usr/bin/env python3
"""정규화된 선거 JSON에서 연도별 '쌍둥이 득표'를 집계한다."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CandidateRecord:
    candidate_id: str
    name: str
    party: str | None
    votes: int


@dataclass(frozen=True)
class UnitRecord:
    dataset_id: str
    country: str
    election_name: str
    election_type: str
    year: int
    round: str | None
    contest_id: str
    contest_name: str
    unit_id: str
    unit_name: str
    level: str
    total_valid_votes: int | None
    candidates: tuple[CandidateRecord, ...]


def _load_dataset(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if "units" not in payload or not isinstance(payload["units"], list):
        raise ValueError(f"{path}: 최상위 'units' 배열이 필요합니다.")
    return payload


def _normalize_candidate(candidate: dict[str, Any]) -> CandidateRecord:
    votes = candidate.get("votes")
    if not isinstance(votes, int):
        raise ValueError("후보자 votes는 정수여야 합니다.")

    candidate_id = str(candidate.get("candidate_id") or candidate.get("name") or "")
    name = str(candidate.get("name") or candidate_id)
    party = candidate.get("party")
    if party is not None:
        party = str(party)

    return CandidateRecord(
        candidate_id=candidate_id,
        name=name,
        party=party,
        votes=votes,
    )


def _normalize_unit(path: Path, payload: dict[str, Any], raw_unit: dict[str, Any]) -> UnitRecord:
    raw_candidates = raw_unit.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ValueError(f"{path}: unit.candidates는 비어 있지 않은 배열이어야 합니다.")

    candidates = tuple(
        sorted(
            (_normalize_candidate(candidate) for candidate in raw_candidates),
            key=lambda item: (-item.votes, item.name, item.candidate_id),
        )
    )

    year = payload.get("year")
    if not isinstance(year, int):
        raise ValueError(f"{path}: 최상위 year는 정수여야 합니다.")

    contest_id = str(raw_unit.get("contest_id") or "")
    contest_name = str(raw_unit.get("contest_name") or contest_id)
    unit_id = str(raw_unit.get("unit_id") or raw_unit.get("unit_name") or "")
    unit_name = str(raw_unit.get("unit_name") or unit_id)
    level = str(raw_unit.get("level") or "unknown")

    total_valid_votes = raw_unit.get("total_valid_votes")
    if total_valid_votes is not None and not isinstance(total_valid_votes, int):
        raise ValueError(f"{path}: total_valid_votes는 정수 또는 null 이어야 합니다.")

    return UnitRecord(
        dataset_id=str(payload.get("dataset_id") or path.stem),
        country=str(payload.get("country") or "unknown"),
        election_name=str(payload.get("election_name") or path.stem),
        election_type=str(payload.get("election_type") or "unknown"),
        year=year,
        round=str(payload["round"]) if payload.get("round") is not None else None,
        contest_id=contest_id,
        contest_name=contest_name,
        unit_id=unit_id,
        unit_name=unit_name,
        level=level,
        total_valid_votes=total_valid_votes,
        candidates=candidates,
    )


def load_units(paths: list[Path]) -> list[UnitRecord]:
    units: list[UnitRecord] = []
    for path in paths:
        payload = _load_dataset(path)
        for raw_unit in payload["units"]:
            units.append(_normalize_unit(path, payload, raw_unit))
    return units


def candidate_vote_signature(unit: UnitRecord) -> list[tuple[str, int]]:
    return [(candidate.name, candidate.votes) for candidate in unit.candidates]


def top_two_signature(unit: UnitRecord) -> tuple[int, ...] | None:
    if len(unit.candidates) < 2:
        return None
    return (unit.candidates[0].votes, unit.candidates[1].votes)


def full_vector_signature(unit: UnitRecord) -> tuple[int, ...]:
    return tuple(candidate.votes for candidate in unit.candidates)


def _base_group_key(unit: UnitRecord) -> tuple[str, int, str, str, str | None, str, str]:
    return (
        unit.country,
        unit.year,
        unit.election_type,
        unit.election_name,
        unit.round,
        unit.contest_id,
        unit.level,
    )


def summarize_candidate_votes(units: list[UnitRecord]) -> dict[str, Any]:
    groups: dict[tuple[str, int, str, str, str | None, str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for unit in units:
        for candidate in unit.candidates:
            groups[_base_group_key(unit) + (candidate.name,)].append(
                {
                    "unit_id": unit.unit_id,
                    "unit_name": unit.unit_name,
                    "votes": candidate.votes,
                }
            )

    findings: list[dict[str, Any]] = []
    yearly_counter: dict[int, int] = defaultdict(int)

    by_group_and_vote: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for group_key, rows in groups.items():
        for row in rows:
            by_group_and_vote[group_key + (row["votes"],)].append(row)

    for key, rows in sorted(by_group_and_vote.items()):
        if len(rows) < 2:
            continue
        country, year, election_type, election_name, round_name, contest_id, level, candidate_name, votes = key
        pair_count = len(rows) * (len(rows) - 1) // 2
        yearly_counter[year] += pair_count
        findings.append(
            {
                "mode": "candidate_votes",
                "country": country,
                "year": year,
                "election_type": election_type,
                "election_name": election_name,
                "round": round_name,
                "contest_id": contest_id,
                "level": level,
                "candidate_name": candidate_name,
                "votes": votes,
                "unit_count": len(rows),
                "pair_count": pair_count,
                "units": sorted(rows, key=lambda row: row["unit_name"]),
            }
        )

    return {
        "mode": "candidate_votes",
        "yearly_pair_counts": dict(sorted(yearly_counter.items())),
        "findings": findings,
    }


def summarize_vector_mode(units: list[UnitRecord], mode: str) -> dict[str, Any]:
    if mode == "top2_vector":
        signature_fn = top_two_signature
    elif mode == "full_vector":
        signature_fn = full_vector_signature
    else:
        raise ValueError(f"지원하지 않는 mode: {mode}")

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    yearly_counter: dict[int, int] = defaultdict(int)
    findings: list[dict[str, Any]] = []

    for unit in units:
        signature = signature_fn(unit)
        if signature is None:
            continue
        groups[_base_group_key(unit) + (signature,)].append(
            {
                "unit_id": unit.unit_id,
                "unit_name": unit.unit_name,
                "signature": list(signature),
                "candidates": [
                    {
                        "name": candidate.name,
                        "party": candidate.party,
                        "votes": candidate.votes,
                    }
                    for candidate in unit.candidates
                ],
            }
        )

    for key, rows in sorted(groups.items()):
        if len(rows) < 2:
            continue
        country, year, election_type, election_name, round_name, contest_id, level, signature = key
        pair_count = len(rows) * (len(rows) - 1) // 2
        yearly_counter[year] += pair_count
        findings.append(
            {
                "mode": mode,
                "country": country,
                "year": year,
                "election_type": election_type,
                "election_name": election_name,
                "round": round_name,
                "contest_id": contest_id,
                "level": level,
                "signature": list(signature),
                "unit_count": len(rows),
                "pair_count": pair_count,
                "units": sorted(rows, key=lambda row: row["unit_name"]),
            }
        )

    return {
        "mode": mode,
        "yearly_pair_counts": dict(sorted(yearly_counter.items())),
        "findings": findings,
    }


def analyze(paths: list[Path], mode: str) -> dict[str, Any]:
    units = load_units(paths)
    if mode == "candidate_votes":
        summary = summarize_candidate_votes(units)
    else:
        summary = summarize_vector_mode(units, mode)

    return {
        "schema_version": 1,
        "input_files": [str(path) for path in paths],
        "unit_count": len(units),
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="정규화된 선거 결과 JSON에서 연도별 쌍둥이 득표를 집계합니다."
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="정규화된 JSON 파일 경로")
    parser.add_argument(
        "--mode",
        choices=("candidate_votes", "top2_vector", "full_vector"),
        default="candidate_votes",
        help=(
            "candidate_votes: 동일 후보 동일 득표수, "
            "top2_vector: 상위 2명 득표 벡터 동일, "
            "full_vector: 전체 후보 득표 벡터 동일"
        ),
    )
    parser.add_argument("--output", type=Path, help="결과 JSON 저장 경로")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = analyze(args.inputs, args.mode)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
