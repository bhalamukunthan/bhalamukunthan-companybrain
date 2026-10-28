# Interview & Resume Prep

## Resume bullets — ONLY use what you have actually run and verified
Replace the bracketed parts with your REAL results (e.g. the numbers printed by `pytest` and `eval_retrieval`):
- Built a multi-tenant RAG knowledge assistant (FastAPI, ChromaDB, Sentence Transformers, Streamlit) that answers employee questions with source citations and abstains when evidence is insufficient.
- Enforced tenant isolation and role-based access by applying metadata filters inside vector search plus server-side checks on every endpoint; wrote [N] pytest tests covering cross-tenant and restricted-document access attempts.
- Evaluated retrieval on a [N]-question dataset ([X]/[Y] hit@k, [Z] permission leaks) and tuned the similarity threshold.

## 60-second explanation
"CompanyBrain is a private assistant for company documents. Admins upload policies; employees ask questions in plain English. The backend splits documents into chunks, turns them into embeddings, and stores them in ChromaDB with metadata: company, allowed roles, page. When someone asks a question, I search with a filter for their company and role so restricted chunks are never retrieved, then answer only from what was found and cite the source. If nothing relevant is found it says so instead of guessing. Security is enforced in the FastAPI backend, not the UI, and I tested cross-company and wrong-role access attempts."

## Questions and simple answers
- **What is RAG?** Look up relevant text first, then answer using only that text, so answers are grounded and citable.
- **What is an embedding?** A list of numbers representing meaning; similar meanings are close together.
- **Why a vector database?** It finds nearest-in-meaning items quickly, unlike exact-match SQL.
- **Why filter during search, not after?** Forbidden text never leaves the database or reaches the model; post-filtering risks leaks and returns fewer useful results.
- **How does multi-tenancy work here?** Every user, document and chunk carries a tenant ID; every query filters on it; cross-tenant lookups return 404.
- **Why return 404 not 403 for hidden documents?** 403 confirms the document exists.
- **How are passwords stored?** bcrypt hashes with per-password salt; never plain text.
- **Why check the role from the DB on each request instead of trusting the token?** Role changes and deletions take effect immediately.
- **What is FastAPI dependency injection?** Reusable functions (like `get_current_user`) that FastAPI runs before the endpoint.
- **How do you reduce hallucination?** Threshold + abstain rule, restrictive prompt, citations, extractive default.
- **What are the limits of the project?** See README: SQLite, no rate limiting, no OCR, heuristic threshold.
- **What would you change for production?** PostgreSQL, TLS, secrets manager, rate limits, audit logs, SSO.
- **Why do your tests use fake embeddings?** To test permissions fast and offline; semantic quality is measured separately by the eval script.
