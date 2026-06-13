#!/usr/bin/env python3
"""선관위 지방선거 XLSX를 정규화 JSON으로 변환한다."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

YEAR_TO_ELECTION_NAME = {
    2010: "제5회 전국동시지방선거",
    2014: "제6회 전국동시지방선거",
    2018: "제7회 전국동시지방선거",
    2022: "제8회 전국동시지방선거",
}

TOTAL_SPECIAL_NAMES = {
    "",
    "합계",
    "계",
    "거소투표",
    "부재자투표",
    "관외사전투표",
    "국외부재자투표",
    "국외부재자신고인명부등재자투표",
    "재외투표",
    "선상투표",
}


def column_index(cell_reference: str) -> int:
    value = 0
    for char in cell_reference:
        if char.isalpha():
            value = value * 26 + ord(char.upper()) - 64
    return value


def clean_text(value: str) -> str:
    return (
        value.replace("_x000D_", "")
        .replace("\r", "")
        .replace("\n", "\n")
        .strip()
    )


def parse_int(value: str) -> int:
    return int(value.replace(",", "").strip())


def parse_candidate_label(value: str) -> tuple[str, str | None]:
    parts = [part.strip() for part in clean_text(value).split("\n") if part.strip()]
    if not parts:
        return "", None
    if len(parts) == 1:
        return parts[0], None
    return parts[-1], parts[0]


def read_shared_strings(archive: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for item in root.findall(f"{NS}si"):
        strings.append("".join(text.text or "" for text in item.iter(f"{NS}t")))
    return strings


def read_sheet_rows(archive: ZipFile, worksheet_path: str, shared_strings: list[str]) -> list[dict[int, str]]:
    root = ET.fromstring(archive.read(f"xl/{worksheet_path}"))
    rows: list[dict[int, str]] = []
    sheet_data = root.find(f"{NS}sheetData")
    if sheet_data is None:
        return rows

    for row in sheet_data.findall(f"{NS}row"):
        row_map: dict[int, str] = {}
        for cell in row.findall(f"{NS}c"):
            reference = cell.attrib.get("r", "")
            index = column_index(reference)
            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                value = shared_strings[int(cell.find(f"{NS}v").text)]
            elif cell_type == "inlineStr":
                inline = cell.find(f"{NS}is")
                value = "".join(text.text or "" for text in inline.iter(f"{NS}t")) if inline is not None else ""
            else:
                node = cell.find(f"{NS}v")
                value = node.text if node is not None else ""
            row_map[index] = clean_text(value)
        rows.append(row_map)
    return rows


def read_workbook(workbook_path: Path) -> list[tuple[str, list[dict[int, str]]]]:
    with ZipFile(workbook_path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        shared_strings = read_shared_strings(archive)
        relation_map = {
            relation.attrib["Id"]: relation.attrib["Target"]
            for relation in relations
        }

        sheets: list[tuple[str, list[dict[int, str]]]] = []
        for sheet in workbook.find(f"{NS}sheets"):
            relation_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            worksheet_path = relation_map[relation_id]
            sheets.append((sheet.attrib["name"], read_sheet_rows(archive, worksheet_path, shared_strings)))
        return sheets


def find_first_data_row(rows: list[dict[int, str]], unit_col: int, division_col: int | None) -> int:
    for index, row in enumerate(rows):
        unit_value = row.get(unit_col, "").strip()
        division_value = row.get(division_col, "").strip() if division_col else ""
        if unit_value in {"합계", "계", "거소투표", "부재자투표", "관외사전투표"}:
            return index
        if division_value in {"소계", "관내사전투표", "선거일투표"}:
            return index
    raise ValueError("데이터 시작 행을 찾지 못했습니다.")


def find_column(row: dict[int, str], names: set[str]) -> int | None:
    for index, value in row.items():
        if value in names:
            return index
    return None


def contest_name_for_row(sheet_name: str, row: dict[int, str], columns: dict[str, int | None]) -> str:
    contest_col = columns.get("contest")
    sido_col = columns.get("sido")
    sigungu_col = columns.get("sigungu")

    if contest_col and row.get(contest_col):
        return row[contest_col]
    if sheet_name in {"시·도지사", "광역의원비례대표", "교육감", "교육의원"} and sido_col:
        return row.get(sido_col, "")
    if sigungu_col:
        return row.get(sigungu_col, "")
    return sheet_name


def classify_channel(unit_name: str, division_value: str) -> str | None:
    if division_value == "소계":
        return "total"
    if division_value == "관내사전투표":
        return "in_person_advance"
    if not division_value and unit_name and unit_name not in TOTAL_SPECIAL_NAMES:
        return "total"
    return None


def build_units_for_sheet(year: int, sheet_name: str, rows: list[dict[int, str]]) -> list[dict[str, object]]:
    if not rows:
        return []

    first_row = rows[0]
    columns = {
        "sido": find_column(first_row, {"시도", "시도명"}),
        "sigungu": find_column(first_row, {"구시군", "구시군명"}),
        "contest": find_column(first_row, {"선거구", "선거구명"}),
        "unit": find_column(first_row, {"읍면동", "읍면동명"}),
        "division": find_column(first_row, {"구분"}),
    }
    if columns["unit"] is None or columns["sido"] is None:
        return []

    invalid_col = None
    for header_row in rows[:3]:
        for index, value in header_row.items():
            if "무효" in value or "무표" in value:
                invalid_col = index
                break
        if invalid_col is not None:
            break
    if invalid_col is None:
        raise ValueError(f"{year} {sheet_name}: 무효투표수 열을 찾지 못했습니다.")

    data_start = find_first_data_row(rows, columns["unit"], columns["division"])
    candidate_header = rows[data_start - 1]
    first_candidate_col = None
    for header_row in rows[:data_start]:
        for index, value in sorted(header_row.items()):
            if index >= invalid_col:
                break
            if "후보자별 득표수" in value or "정당별 득표수" in value:
                first_candidate_col = index
                break
        if first_candidate_col is not None:
            break
    if first_candidate_col is None:
        raise ValueError(f"{year} {sheet_name}: 후보자 시작 열을 찾지 못했습니다.")

    candidate_columns: list[tuple[int, str, str | None]] = []
    for index in range(first_candidate_col, invalid_col - 1):
        name, party = parse_candidate_label(candidate_header.get(index, ""))
        if name:
            candidate_columns.append((index, name, party))

    units: list[dict[str, object]] = []
    for row in rows[data_start:]:
        unit_name = row.get(columns["unit"], "").strip()
        division_value = row.get(columns["division"], "").strip() if columns["division"] else ""
        channel = classify_channel(unit_name, division_value)
        if channel is None:
            continue

        contest_name = contest_name_for_row(sheet_name, row, columns)
        sido_name = row.get(columns["sido"], "").strip()
        sigungu_name = row.get(columns["sigungu"], "").strip() if columns["sigungu"] else ""

        candidates = []
        total_valid_votes = 0
        for column_index_value, candidate_name, party in candidate_columns:
            raw_votes = row.get(column_index_value, "0").strip() or "0"
            votes = parse_int(raw_votes)
            total_valid_votes += votes
            candidates.append(
                {
                    "candidate_id": f"{party or '무소속'}::{candidate_name}",
                    "name": candidate_name,
                    "party": party,
                    "votes": votes,
                }
            )

        units.append(
            {
                "contest_id": f"{sheet_name}:{contest_name}",
                "contest_name": f"{sheet_name} {contest_name}".strip(),
                "unit_id": f"{year}:{sheet_name}:{contest_name}:{sido_name}:{sigungu_name}:{unit_name}:{channel}",
                "unit_name": f"{sido_name} {sigungu_name} {unit_name}".strip(),
                "level": "dong",
                "vote_channel": channel,
                "total_valid_votes": total_valid_votes,
                "candidates": candidates,
            }
        )
    return units


def build_dataset(year: int, source_path: Path, vote_channel: str) -> dict[str, object]:
    all_units = []
    for sheet_name, rows in read_workbook(source_path):
        if sheet_name == "국회의원재보궐":
            continue
        all_units.extend(build_units_for_sheet(year, sheet_name, rows))

    filtered_units = [
        unit
        for unit in all_units
        if unit["vote_channel"] == vote_channel
    ]
    for unit in filtered_units:
        unit.pop("vote_channel", None)

    return {
        "dataset_id": f"kr-local-{year}-{vote_channel}",
        "country": "KR",
        "election_name": YEAR_TO_ELECTION_NAME[year],
        "election_type": "local",
        "year": year,
        "round": "general",
        "units": filtered_units,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="선관위 지방선거 XLSX를 정규화 JSON으로 변환합니다.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw/nec-local"),
        help="원본 XLSX 디렉터리",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/historical"),
        help="정규화 JSON 출력 디렉터리",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for year in sorted(YEAR_TO_ELECTION_NAME):
        source_path = args.input_dir / f"{year}-local.xlsx"
        if not source_path.exists():
            continue
        for vote_channel in ("total", "in_person_advance"):
            dataset = build_dataset(year, source_path, vote_channel)
            output_path = args.output_dir / f"kr-local-{year}-{vote_channel}.json"
            output_path.write_text(
                json.dumps(dataset, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"JSON 저장: {output_path} ({len(dataset['units'])} units)")


if __name__ == "__main__":
    main()
