"""Evaluation: measure retrieval recall and refusal on a test set."""
from retrieval import retrieve

# Each test: a question and a word that must appear in the correct chunk.
# "has": None means the answer is NOT in the documents -> system must refuse.
TESTS = [
    {"q": "How do I register for courses?", "has": "portal"},
    {"q": "When is late registration allowed?", "has": "first week"},
    {"q": "Who approves late registration?", "has": "department head"},
    {"q": "What GPA do I need to graduate?", "has": "2.0"},
    {"q": "What courses must I finish to graduate?", "has": "required courses"},
    {"q": "كيف أسجل المساقات؟", "has": "بوابة"},
    {"q": "مين لازم يوافق على التسجيل المتأخر؟", "has": "رئيس الدائرة"},
    {"q": "شو المعدل المطلوب للتخرج؟", "has": "2.0"},
    {"q": "Who won the 2022 World Cup?", "has": None},
    {"q": "What is the best restaurant in Bethlehem?", "has": None},
]


def evaluate(k=3):
    found = in_scope = refused = out_scope = 0
    failures = []
    for t in TESTS:
        hits = retrieve(t["q"], k=k)
        if t["has"] is None:
            out_scope += 1
            if not hits:
                refused += 1
            else:
                failures.append(f"should refuse: {t['q']}")
        else:
            in_scope += 1
            if any(t["has"].lower() in h["text"].lower() for h in hits):
                found += 1
            else:
                failures.append(f"not found: {t['q']}")
    print(f"\nk={k} | Recall@{k}: {found}/{in_scope} ({found / in_scope:.0%})"
          f" | Refusal: {refused}/{out_scope}")
    for f in failures:
        print("  FAILED ->", f)


if __name__ == "__main__":
    for k in (1, 3):
        evaluate(k)