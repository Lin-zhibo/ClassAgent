import csv
import re
from pathlib import Path


def split_poet_work(value: str) -> tuple[str, str]:
    text = (value or "").strip()
    match = re.match(r"^(.*?)《(.*?)》$", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return text, ""


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "data" / "questions.CSV"
    output_csv_path = csv_path.with_name(f"new_{csv_path.name}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    output_rows = []
    for row in rows:
        poet_work = (row.get("诗人作品", "") or "").strip()
        if poet_work:
            poet, work = split_poet_work(poet_work)
        else:
            poet = (row.get("诗人", "") or "").strip()
            work = (row.get("作品", "") or "").strip()
        output_rows.append(
            {
                "诗人": poet,
                "作品": work,
                "问题": row.get("问题", ""),
                "答案": row.get("答案", ""),
            }
        )

    with output_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["诗人", "作品", "问题", "答案"])
        writer.writeheader()
        writer.writerows(output_rows)


if __name__ == "__main__":
    main()
