# Listening App Backend (FastAPI Minimal Prototype)

## Features
- Materials upload (audio + transcript)
- Auto sentence split
- Task creation (bundle of sentences)
- Submissions: shadowing, dictation, retelling, summary
- Lightweight scoring (no heavy ML): rapidfuzz for string similarity, keyword coverage, timing placeholders
- SQLite via SQLAlchemy

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```
The server runs at `http://127.0.0.1:8000` (CORS enabled for `http://localhost:5173` and `http://localhost:3000`).

## Key Endpoints
- `POST /materials`: upload audio (multipart) + transcript
- `POST /materials/{id}/split`: auto-split transcript into sentences
- `POST /tasks`: create a task from a material (choose modes)
- `GET  /tasks/{id}`: task detail with sentences
- `POST /submit/dictation`: grade dictation
- `POST /submit/shadowing`: score shadowing (placeholder using length + timing fields)
- `POST /submit/retell`: semantic coverage via keyword overlap
- `POST /submit/summary`: summary coverage/structure heuristics
- `GET  /reports/user/{user_id}`: aggregate basic metrics

See inline docstrings for payloads.
```

## Notes
- This is a prototype to unblock front-end integration. Replace placeholder scoring with ASR/alignment later.