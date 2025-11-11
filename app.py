from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os, json
from database import engine, Base, get_db
from models import Material, Task, Sentence, Submission
from schemas import *  # noqa
from utils import split_sentences, grade_dictation, grade_retell, grade_summary

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Listening App Backend", version="0.1.0")
origins = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/materials", response_model=MaterialOut)
async def create_material(title: str = Form(...), transcript: str = Form(...), audio: UploadFile = File(None), db: Session = Depends(get_db)):
    path = None
    if audio is not None:
        filename = f"{title.replace(' ','_')}_{audio.filename}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, 'wb') as f:
            f.write(await audio.read())
    m = Material(title=title, transcript=transcript, audio_path=path)
    db.add(m)
    db.commit(); db.refresh(m)
    return m

@app.post("/materials/{mid}/split")
def material_split(mid: int, req: SplitRequest, db: Session = Depends(get_db)):
    m = db.get(Material, mid)
    if not m: raise HTTPException(404, "Material not found")
    sents = split_sentences(m.transcript)
    # clear old
    db.query(Sentence).filter(Sentence.material_id==mid).delete()
    for i, s in enumerate(sents):
        db.add(Sentence(material_id=mid, order=i+1, text=s))
    db.commit()
    return {"count": len(sents)}

@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    t = Task(title=task.title, material_id=task.material_id, modes=','.join(task.modes), difficulty=task.difficulty)
    db.add(t); db.commit(); db.refresh(t)
    return TaskOut(id=t.id, title=t.title, material_id=t.material_id, modes=t.modes.split(','), difficulty=t.difficulty)

@app.get("/tasks/{tid}")
def get_task(tid: int, db: Session = Depends(get_db)):
    t = db.get(Task, tid)
    if not t: raise HTTPException(404, "Task not found")
    sents = db.query(Sentence).filter(Sentence.material_id==t.material_id).order_by(Sentence.order).all()
    return {
        "id": t.id,
        "title": t.title,
        "modes": t.modes.split(','),
        "difficulty": t.difficulty,
        "sentences": [{"id": s.id, "order": s.order, "text": s.text} for s in sents]
    }

@app.post("/submit/dictation")
def submit_dictation(payload: DictationSubmit, db: Session = Depends(get_db)):
    score, diffs = grade_dictation(payload.expected, payload.text)
    sub = Submission(user_id=payload.user_id, task_id=payload.task_id, type='dictation', sentence_id=payload.sentence_id, payload=json.dumps(payload.model_dump()), score=score)
    db.add(sub); db.commit()
    return {"score": score, "diffs": diffs, "submission_id": sub.id}

@app.post("/submit/shadowing")
def submit_shadowing(payload: ShadowingSubmit, db: Session = Depends(get_db)):
    # placeholder: closer duration to reference → higher score
    ref = max(1, payload.reference_ms)
    diff = abs(payload.duration_ms - ref) / ref
    score = max(0.0, 100.0 * (1 - min(1.0, diff)))
    sub = Submission(user_id=payload.user_id, task_id=payload.task_id, type='shadowing', sentence_id=payload.sentence_id, payload=json.dumps(payload.model_dump()), score=round(score,2))
    db.add(sub); db.commit()
    return {"score": round(score,2), "submission_id": sub.id}

@app.post("/submit/retell")
def submit_retell(payload: RetellSubmit, db: Session = Depends(get_db)):
    score = grade_retell(payload.reference, payload.text)
    sub = Submission(user_id=payload.user_id, task_id=payload.task_id, type='retell', sentence_id=payload.sentence_id, payload=json.dumps(payload.model_dump()), score=score)
    db.add(sub); db.commit()
    return {"score": score, "submission_id": sub.id}

@app.post("/submit/summary")
def submit_summary(payload: SummarySubmit, db: Session = Depends(get_db)):
    score = grade_summary(payload.reference, payload.text)
    sub = Submission(user_id=payload.user_id, task_id=payload.task_id, type='summary', payload=json.dumps(payload.model_dump()), score=score)
    db.add(sub); db.commit()
    return {"score": score, "submission_id": sub.id}

@app.get("/reports/user/{user_id}")
def user_report(user_id: str, db: Session = Depends(get_db)):
    subs = db.query(Submission).filter(Submission.user_id==user_id).all()
    by_type = {}
    for s in subs:
        by_type.setdefault(s.type, []).append(s.score)
    summary = {k: round(sum(v)/len(v),2) for k,v in by_type.items() if v}
    return {"count": len(subs), "average_by_type": summary}