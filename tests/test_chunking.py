"""Chunking and PDF-line rules of the RAG core. Plain Python: no models, index or network."""
from django.test import SimpleTestCase

from rag.infrastructure.chunker import make_chunks
from rag.infrastructure.loaders import WRAPPED_LINE, Block, is_heading

SECTION = "3. DEGREE REQUIREMENTS"


def blocks(lines, section=SECTION, kind="text"):
    return [Block(line, 1, section, kind) for line in lines]


TABLE = [f"Bachelor of Science in Program number {n} {120 + n}" for n in range(12)]
RULES = (["To receive a degree from the University a student", "must complete:",
          "1. The University Requirements.", "2. A minimum GPA of 2.00.",
          "5. Minimum credit hours for degrees:"]
         + TABLE + ["6. A minimum of 60 credits at the University.", "7. All obligations."])


class ChunkingTests(SimpleTestCase):
    def test_numbered_rule_after_a_table_starts_a_new_chunk_with_the_list_lead_in(self):
        chunks = make_chunks("doc.pdf", "Catalog", blocks(RULES), 900)
        rule6 = next(c for c in chunks if "60 credits" in c.text)
        body = rule6.text.split("\n")
        self.assertEqual(body[1], "To receive a degree from the University a student must complete: (…)")
        self.assertTrue(body[2].startswith("6. A minimum of 60 credits"))
        self.assertNotIn("Program number", rule6.text)

    def test_first_chunk_of_a_list_has_no_repeated_lead_in(self):
        chunks = make_chunks("doc.pdf", "Catalog", blocks(RULES), 900)
        self.assertNotIn("(…)", chunks[0].text)

    def test_tiny_leftovers_join_the_next_chunk(self):
        parts = (blocks(["First Year"], "FALL SEMESTER") + blocks(["CR"], "SPRING SEMESTER")
                 + blocks(["ENGL 120 English Language Skills I 3"] * 5, "SPRING SEMESTER"))
        chunks = make_chunks("doc.pdf", "Catalog", parts, 900)
        self.assertEqual(len(chunks), 1)
        self.assertIn("First Year", chunks[0].text)
        self.assertEqual(chunks[0].section, "SPRING SEMESTER")

    def test_table_rows_and_prose_are_separate_chunks(self):
        prose = blocks(["Students must attend all classes and may not miss more than 15% of them."] * 2)
        rows = blocks(["Course: ARAB 120، Credits: 3"] * 4, kind="table")
        chunks = make_chunks("doc.pdf", "Catalog", prose + rows, 900)
        self.assertEqual(len(chunks), 2)
        self.assertNotIn("Course:", chunks[0].text)

    def test_course_codes_are_not_headings_and_wrapped_lines_are_detected(self):
        self.assertFalse(is_heading("ARAB 120"))
        self.assertTrue(is_heading("STUDENT REGULATIONS"))
        self.assertTrue(WRAPPED_LINE.match("minimum of 60 credits at Bethlehem University."))
        for marker in ("a. Status:", "(ii) Students on Probation", "Faculty of Arts"):
            self.assertIsNone(WRAPPED_LINE.match(marker), marker)
