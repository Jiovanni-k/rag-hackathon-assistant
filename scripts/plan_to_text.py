"""Convert a university study-plan web page (HTML tables) into clean text for the RAG index.

Each course becomes one self-contained line, so a chunk never splits a course from its hours
or prerequisites, and prerequisite codes are resolved to course names.

Usage:
    python scripts/plan_to_text.py URL_OR_FILE --university "جامعة النجاح الوطنية" \
        --program "بكالوريوس القانون" --out documents/Najah_Law_Study_Plan.txt
"""
import argparse
import re
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_HOURS = re.compile(r"(يجب على الطالب|Student must complete|تتكون الخطة)", re.I)
TOTAL_HOURS = re.compile(r"(\d+)\)?\s*(ساعة معتمدة|credit hours)", re.I)
COLUMNS = {  # column role -> words that identify its header cell
    "code": ("رقم المساق", "رمز المساق", "course code"),
    "name": ("اسم المساق", "course name"),
    "hours": ("الساعات", "عدد الساعات", "credit hours"),
    "prereq": ("المتطلب", "المتطلبات", "prereq"),
}


class PlanParser(HTMLParser):
    """Collects every table, plus the last few text lines that appeared before it."""

    def __init__(self):
        super().__init__()
        self.texts, self.tables = [], []
        self.depth, self.skip = 0, False
        self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip = True
        elif tag == "table":
            if self.depth == 0:
                self.tables.append({"context": self.texts[-6:], "rows": []})
            self.depth += 1
        elif tag == "tr" and self.depth:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = False
        elif tag == "table":
            self.depth -= 1
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell.split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if any(self.row):
                self.tables[-1]["rows"].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell += data
        elif not self.depth and data.strip():
            self.texts.append(" ".join(data.split()))


def heading_for(context):
    """Build a section title such as 'السنة الأولى - الفصل الثاني' or 'متطلبات تخصص (96 ساعة)'."""
    if not context:
        return "مساقات"
    last = context[-1]
    if REQUIRED_HOURS.search(last) and len(context) > 1:
        return f"{context[-2]} — {last}"
    if last.startswith("الفصل"):
        year = next((t for t in reversed(context[:-1]) if t.startswith("السنة")), "")
        return f"{year} - {last}" if year else last
    return last


def column_map(header):
    roles = {}
    for i, cell in enumerate(header):
        low = cell.lower()
        for role, words in COLUMNS.items():
            if role not in roles and any(w in low for w in words):
                roles[role] = i
                break
    return roles if {"code", "name"} <= roles.keys() else None


def parse_courses(tables):
    """Return [(heading, [course dict, ...])] and a code -> name lookup."""
    sections, names = [], {}
    for table in tables:
        rows = table["rows"]
        if not rows or not (roles := column_map(rows[0])):
            continue
        courses, total = [], None
        for row in rows[1:]:
            if len(row) == 1:                      # a description row under the previous course
                if courses and not row[0].startswith("المجموع"):
                    courses[-1]["desc"] = row[0]
                continue
            get = lambda r: row[roles[r]] if r in roles and roles[r] < len(row) else ""
            course = {"code": get("code"), "name": get("name"), "hours": get("hours"),
                      "prereq": re.findall(r"\d{5,}", get("prereq")), "desc": ""}
            if course["name"].startswith("المجموع"):   # the page's own total for this table
                total = course["hours"]
            elif course["name"]:                       # no code = an open slot, e.g. «متطلب جامعة اجباري»
                courses.append(course)
                if course["code"]:
                    names[course["code"]] = course["name"]
        if courses:
            sections.append((heading_for(table["context"]), courses, total))
    return sections, names


def course_line(c, names, program):
    if not c["code"]:
        return (f"- [{program}] مساق تختاره من فئة «{c['name']}»: "
                f"{c['hours'] or '؟'} ساعات معتمدة.")
    prereq = "، ".join(f"{p} «{names[p]}»" if p in names else p for p in c["prereq"])
    line = (f"- [{program}] المساق {c['code']} «{c['name']}»: {c['hours'] or '؟'} ساعات معتمدة. "
            f"المتطلب السابق: {prereq or 'لا يوجد'}.")
    if c["desc"]:
        line += f"\n  الوصف: {c['desc']}"
    return line


def read_source(src):
    if Path(src).exists():
        return Path(src).read_text(encoding="utf-8")
    req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def convert(src, university, program, source_url=None):
    parser = PlanParser()
    parser.feed(read_source(src))
    sections, names = parse_courses(parser.tables)
    if not sections:
        raise SystemExit("No course tables found on this page.")
    total = next((m.group(1) for t in parser.texts if REQUIRED_HOURS.search(t)
                  and (m := TOTAL_HOURS.search(t))), None)

    out = [f"# {university} — {program}",
           f"المصدر: {source_url or src}",
           f"تاريخ الجلب: {date.today().isoformat()}"]
    if total:
        out.append(f"مجموع الساعات المعتمدة المطلوبة للتخرج في {program}: {total} ساعة معتمدة.")
    for heading, courses, table_total in sections:
        out += ["", f"## {program} — {heading}"]
        # Only a semester table is a real load; requirement tables list elective options too,
        # so summing them would overstate the required hours. Prefer the page's own total.
        if heading.startswith(("السنة", "الفصل")):
            hours = table_total or sum(int(c["hours"]) for c in courses if c["hours"].isdigit())
            out.append(f"عبء {heading} في الخطة الاسترشادية لـ{program}: "
                       f"{len(courses)} مساقات بمجموع {hours} ساعة معتمدة.")
        out += [course_line(c, names, program) for c in courses]
    return "\n".join(out) + "\n", sum(len(c) for _, c, _ in sections)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="URL or local .html file")
    ap.add_argument("--university", required=True)
    ap.add_argument("--program", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source-url", help="original URL when converting a saved file")
    args = ap.parse_args()
    text, n = convert(args.source, args.university, args.program, args.source_url)
    Path(args.out).write_text(text, encoding="utf-8")
    print(f"{args.out}: {n} courses")
