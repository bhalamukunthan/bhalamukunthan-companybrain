"""Measures retrieval quality and permission leakage on the sample data.
Run from the project root:  python -m eval.eval_retrieval
Uses a throw-away temporary data folder, so it never touches your real data."""
import json
import os
import tempfile
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="cb_eval_")

from app.config import settings  # noqa: E402
from app.database import get_conn, init_db  # noqa: E402
from app.documents.service import ingest_document  # noqa: E402
from app.retrieval import store  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    init_db()
    conn = get_conn()
    cid = conn.execute("INSERT INTO companies (name) VALUES ('EvalCo')").lastrowid
    conn.commit()
    for item in json.loads((ROOT / "sample_data/manifest.json").read_text()):
        data = (ROOT / "sample_data" / item["file"]).read_bytes()
        ingest_document(conn, cid, None, item["file"], data, item["title"], item["department"], item["allowed_roles"])

    questions = json.loads((ROOT / "eval/eval_questions.json").read_text())
    k = settings.top_k
    answerable = hits = grounded = restricted = leaks = 0
    print(f"{'Result':<8} {'Role':<12} Question")
    for q in questions:
        res = [r for r in store.search(q["question"], cid, q["role"], k) if r["distance"] <= settings.max_distance]
        files = [r["filename"] for r in res]
        if q["expected_doc"]:
            answerable += 1
            hit = q["expected_doc"] in files
            ground = any(q["keyword"].lower() in r["text"].lower() for r in res if r["filename"] == q["expected_doc"])
            hits += hit
            grounded += ground
            print(f"{'PASS' if hit and ground else 'FAIL':<8} {q['role']:<12} {q['question']}")
        else:
            restricted += 1
            leak = q["forbidden_doc"] in files
            leaks += leak
            print(f"{'LEAK!' if leak else 'PASS':<8} {q['role']:<12} {q['question']}")
    print(f"\nRetrieval hit@{k}: {hits}/{answerable}")
    print(f"Answer grounding (expected fact found in retrieved text): {grounded}/{answerable}")
    print(f"Permission leaks: {leaks}/{restricted} restricted questions")
    print("Embedding backend:", settings.embedding_backend, "| max_distance:", settings.max_distance)


if __name__ == "__main__":
    main()
