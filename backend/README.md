# PaceAlyzer Backend

FastAPI backend for PaceAlyzer. It contains the multi-agent workflow, RAG retrieval service, persistence tools, Strava/metrics services and experiment scripts.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Required Environment Variables

- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `ENV`

Optional variables for evaluation scripts:

- `PACEALYZER_E2E_USER_ID`
- `E2E_TEST_USER_ID`

## Useful Scripts

- `scripts/seed_library.py`: seed the workout library.
- `scripts/regenerate_embeddings.py`: regenerate canonical workout embeddings.
- `scripts/import_zwo.py`: import `.zwo` workout files.
- `scripts/experiments/evaluate_librarian_rag.py`: evaluate the RAG retrieval pipeline.
- `scripts/experiments/evaluate_operator_routing.py`: evaluate operator routing.
- `scripts/experiments/evaluate_end_to_end.py`: evaluate end-to-end system behavior.

