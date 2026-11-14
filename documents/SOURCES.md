# Document sources

Public documents used for development and testing. All were retrieved on 2026-11-07 from the
universities' official websites and remain the property of their publishers. Replace or extend them
with your own university's documents (see the README, section "Data").

| File | University | Content | Source |
|---|---|---|---|
| `BU_English_Catalog.pdf` | Bethlehem University | Catalog: academic and student regulations, programs, courses (English) | https://reg.bethlehem.edu:100/docs/English_Catalog_20127df0.pdf |
| `BU_Grading_Rules_AR.pdf` | Bethlehem University | Grading instructions for instructors (English text despite the Arabic title) | https://bethlehem.edu/wp-content/uploads/2024/05/Grading-تعليمات-وضع-العلامات.pdf |
| `BU_Final_Exam_Proctoring_2024.pdf` | Bethlehem University | Final exam proctoring rules | https://bethlehem.edu/wp-content/uploads/2024/06/Proctoring-FEx-2024.pdf |
| `PTUK_Computer_Science_Study_Plan.txt` | Palestine Technical University – Kadoorie | B.Sc. Computer Science study plan (requirement groups, courses, hours, prerequisites) | https://ptuk.edu.ps/ar/academic-programs/study-plan.php?name=bachelor-of-computer-science |
| `PTUK_Computer_Science_Advising_Plan.txt` | Palestine Technical University – Kadoorie | B.Sc. Computer Science advising plan, semester by semester | https://ptuk.edu.ps/ar/academic-programs/advising-plan.php?name=bachelor-of-computer-science |
| `Najah_Law_Study_Plan.txt` | An-Najah National University | Bachelor of Law study plan (139 credit hours) with course descriptions | https://www.najah.edu/ar/academic/undergraduate-programs/program/law/study-plan/ |
| `Najah_Medicine_Study_Plan.txt` | An-Najah National University | Doctor of Medicine study plan (266 credit hours) with course descriptions (English) | https://www.najah.edu/ar/academic/undergraduate-programs/program/medicine/study-plan/ |

The `.txt` study plans were generated from the HTML pages with `scripts/plan_to_text.py`.

## Not indexed (kept in `test_docs_ar/` for testing)

| File | Why | Source |
|---|---|---|
| `AABU_Student_Guide_AR.pdf` | Arabic PDF extraction tests (Al al-Bayt University, Jordan; different institution) | https://student.aabu.edu.jo/nreg/del2021-2022.pdf |
| `Najah_Medicine_Old_vs_New_Plan.pdf` | Side-by-side old/new medicine plan; test case for version conflicts | https://fmhs.najah.edu/media/filer_public/a2/af/a2afdeb7-39a4-4f90-9d2d-3dfaaf3bee53/study_plan.pdf |

## Known issues in the sources
- PTUK Computer Science: the page states 135 credit hours, but its requirement groups add up to 138
  and the advising plan semesters add up to 132.
- An-Najah Medicine: the page is in English even on the Arabic site.
