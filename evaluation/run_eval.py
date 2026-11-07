"""End-to-end evaluation of the RAG system on evaluation/test_set.json.

Checks per question:
  retrieval - an expected text appears in the retrieved chunks (in-scope questions)
  answer    - every expected value appears in the final answer
  refusal   - out-of-docs / out-of-scope questions are refused, in-scope ones are not

Usage:  python -m evaluation.run_eval            (writes evaluation/results/latest.json)
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from rag import config
from rag.application.ask_service import ask
from rag.infrastructure.arabic import clean_text

HERE = Path(__file__).parent


def check(case, ans):
    should_refuse = case.get("refuse", False)
    result = {"refusal_ok": ans.refused == should_refuse}
    if not should_refuse:
        texts = " ".join(ans.retrieved)
        result["retrieval_ok"] = any(s in texts for s in case.get("retrieve_any", [])) \
            if case.get("retrieve_any") else None
        answer = clean_text(ans.text)
        result["answer_ok"] = (not ans.refused) and all(s in answer for s in case.get("answer_all", []))
    result["passed"] = all(v for v in result.values() if v is not None)
    return result


def main():
    cases = json.loads((HERE / "test_set.json").read_text(encoding="utf-8"))
    rows, by_type = [], defaultdict(lambda: [0, 0])
    for case in cases:
        t = time.time()
        ans = ask(case["question"], case.get("history"))
        latency = time.time() - t
        res = check(case, ans)
        by_type[case["type"]][0] += res["passed"]
        by_type[case["type"]][1] += 1
        rows.append({**case, **res, "latency_s": round(latency, 1), "reason": ans.reason,
                     "best_distance": round(ans.best_distance, 3), "answer": ans.text,
                     "standalone": ans.standalone_question,
                     "sources": [s.label() for s in ans.sources]})
        mark = "PASS" if res["passed"] else "FAIL"
        flags = " ".join(f"{k[:-3]}={'ok' if v else 'X'}" for k, v in res.items()
                         if k.endswith("_ok") and v is not None)
        print(f"{mark} #{case['id']:<2} {case['type']:<12} d={ans.best_distance:.3f} {latency:4.1f}s "
              f"{ans.reason:<14} {flags}")
        if not res["passed"]:
            print(f"      Q: {case['question']}\n      standalone: {ans.standalone_question}"
                  f"\n      A: {' '.join(ans.text.split())[:220]}")

    passed = sum(r["passed"] for r in rows)
    print(f"\nPASSED {passed}/{len(rows)}   (MAX_DIST={config.MAX_DIST}, model={config.EMBED_MODEL})")
    for t, (p, n) in by_type.items():
        print(f"  {t:<13} {p}/{n}")
    in_scope = [r["best_distance"] for r in rows if not r.get("refuse")]
    refuse = [r["best_distance"] for r in rows if r.get("refuse") and r["reason"] != "out_of_scope"]
    if in_scope and refuse:
        print(f"  distance: in-scope max={max(in_scope):.3f} | should-refuse min={min(refuse):.3f}")
    print(f"  avg latency: {sum(r['latency_s'] for r in rows) / len(rows):.1f}s")

    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "latest.json").write_text(json.dumps(
        {"passed": passed, "total": len(rows), "max_dist": config.MAX_DIST,
         "embed_model": config.EMBED_MODEL, "results": rows}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
