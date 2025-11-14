from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import os, json
from database import engine, Base, get_db
from models import Material, Task, Sentence, Submission
from schemas import *
from utils import split_sentences, grade_dictation, grade_retell, grade_summary

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Listening App Backend", version="0.1.0")

# CORS allowed origins
origins = [
    "*",   # 允许所有来源（方便前端访问）
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload folder
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -----------------------------
#  🚀 MATERIAL UPLOAD (audio optional)
# -----------------------------
@app.post("/materials", response_model=MaterialOut)
async def create_material(
    title: str = Form(...),
    transcript: str = Form(None),
    text: str = Form(None),      # 支持前端 text 字段
    audio: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # 合并 transcript 和 text
    final_text = transcript or text
    if final_text is None:
        raise HTTPException(400, "Transcript or text is required.")

    # 处理音频（可选）
    audio_path = None
    if audio and audio.filename:
        filename = f"{title.replace(' ','_')}_{audio.filename}"
        audio_path = os.path.join(UPLOAD_DIR, filename)
        with open(audio_path, "wb") as f:
            f.write(await audio.read())

    # 保存到数据库
    m = Material(title=title, transcript=final_text, audio_path=audio_path)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# -----------------------------
#  ✂️ MATERIAL SPLIT
# -----------------------------
@app.post("/materials/{mid}/split")
def material_split(mid: int, req: SplitRequest, db: Session = Depends(get_db)):
    m = db.get(Material, mid)
    if not m:
        raise HTTPException(404, "Material not found")

    sentences = split_sentences(m.transcript)

    # delete old ones
    db.query(Sentence).filter(Sentence.material_id == mid).delete()

    # save new ones
    for i, s in enumerate(sentences):
        db.add(Sentence(material_id=mid, order=i+1, text=s))

    db.commit()
    return {"count": len(sentences)}


# -----------------------------
#  📘 CREATE TASK
# -----------------------------
@app.post("/tasks", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    t = Task(
        title=task.title,
        material_id=task.material_id,
        modes=",".join(task.modes),
        difficulty=task.difficulty,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return TaskOut(
        id=t.id,
        title=t.title,
        material_id=t.material_id,
        modes=t.modes.split(","),
        difficulty=t.difficulty
    )


# -----------------------------
#  📘 GET TASK
# -----------------------------
@app.get("/tasks/{tid}")
def get_task(tid: int, db: Session = Depends(get_db)):
    t = db.get(Task, tid)
    if not t:
        raise HTTPException(404, "Task not found")

    sents = db.query(Sentence).filter(
        Sentence.material_id == t.material_id
    ).order_by(Sentence.order).all()

    return {
        "id": t.id,
        "title": t.title,
        "modes": t.modes.split(","),
        "difficulty": t.difficulty,
        "sentences": [
            {"id": s.id, "order": s.order, "text": s.text}
            for s in sents
        ]
    }


# -----------------------------
#  📝 SUBMIT DICTATION
# -----------------------------
@app.post("/submit/dictation")
def submit_dictation(payload: DictationSubmit, db: Session = Depends(get_db)):
    score, diffs = grade_dictation(payload.expected, payload.text)

    sub = Submission(
        user_id=payload.user_id,
        task_id=payload.task_id,
        type="dictation",
        sentence_id=payload.sentence_id,
        payload=json.dumps(payload.model_dump()),
        score=score
    )
    db.add(sub)
    db.commit()

    return {"score": score, "diffs": diffs, "submission_id": sub.id}


# -----------------------------
#  🎤 SUBMIT SHADOWING
# -----------------------------
@app.post("/submit/shadowing")
def submit_shadowing(payload: ShadowingSubmit, db: Session = Depends(get_db)):
    reference = max(1, payload.reference_ms)
    diff = abs(payload.duration_ms - reference) / reference
    score = max(0, 100 * (1 - min(1, diff)))

    sub = Submission(
        user_id=payload.user_id,
        task_id=payload.task_id,
        type="shadowing",
        sentence_id=payload.sentence_id,
        payload=json.dumps(payload.model_dump()),
        score=round(score, 2)
    )
    db.add(sub)
    db.commit()

    return {"score": round(score, 2), "submission_id": sub.id}


# -----------------------------
#  📖 SUBMIT RETELL
# -----------------------------
@app.post("/submit/retell")
def submit_retell(payload: RetellSubmit, db: Session = Depends(get_db)):
    score = grade_retell(payload.reference, payload.text)

    sub = Submission(
        user_id=payload.user_id,
        task_id=payload.task_id,
        type="retell",
        sentence_id=payload.sentence_id,
        payload=json.dumps(payload.model_dump()),
        score=score
    )
    db.add(sub)
    db.commit()

    return {"score": score, "submission_id": sub.id}


# -----------------------------
#  📚 SUBMIT SUMMARY
# -----------------------------
@app.post("/submit/summary")
def submit_summary(payload: SummarySubmit, db: Session = Depends(get_db)):
    score = grade_summary(payload.reference, payload.text)

    sub = Submission(
        user_id=payload.user_id,
        task_id=payload.task_id,
        type="summary",
        payload=json.dumps(payload.model_dump()),
        score=score
    )
    db.add(sub)
    db.commit()

    return {"score": score, "submission_id": sub.id}


# -----------------------------
#  📊 USER REPORT
# -----------------------------
@app.get("/reports/user/{user_id}")
def user_report(user_id: str, db: Session = Depends(get_db)):
    subs = db.query(Submission).filter(Submission.user_id == user_id).all()

    by_type = {}
    for s in subs:
        by_type.setdefault(s.type, []).append(s.score)

    summary = {k: round(sum(v)/len(v), 2) for k, v in by_type.items()}

    return {"count": len(subs), "average_by_type": summary}

# ============================
# 🧑‍🏫 Student Accounts System
# ============================

STUDENT_DB_PATH = os.path.join(os.path.dirname(__file__), "students.json")

# 如果没有文件，自动创建
if not os.path.exists(STUDENT_DB_PATH):
    with open(STUDENT_DB_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


# 1) 获取所有学生
@app.get("/students")
def get_students():
    with open(STUDENT_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# 2) 添加学生
@app.post("/students/add")
def add_student(data: dict):
    with open(STUDENT_DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    username = data.get("username")
    if username in db:
        return "❌ 用户名已存在"

    db[username] = {
        "password": data.get("password"),
        "email": data.get("email"),
        "phone": data.get("phone")
    }

    with open(STUDENT_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    return "✅ 添加成功"


# 3) 重置密码
@app.post("/students/reset")
def reset_password(data: dict):
    with open(STUDENT_DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    username = data.get("username")
    if username not in db:
        return "❌ 用户不存在"

    db[username]["password"] = data.get("new_password")

    with open(STUDENT_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    return "🔑 密码重置成功"

# 给某个学生分配任务
@app.post("/assign")
def assign_task(data: dict):
    username = data.get("username")
    task_id = data.get("task_id")

    # 读取 student_tasks.json
    path = os.path.join(os.path.dirname(__file__), "student_tasks.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)

    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    # 添加
    db.setdefault(username, [])
    if task_id not in db[username]:
        db[username].append(task_id)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    return {"message": "Assigned successfully"}


# 获取一个学生的任务
@app.get("/assign/{username}")
def get_user_tasks(username: str):
    path = os.path.join(os.path.dirname(__file__), "student_tasks.json")

    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        db = json.load(f)

    return db.get(username, [])
# ============================
# 🏠 Home (root) endpoint
# ============================
@app.get("/")
def home():
    return {
        "status": "Backend running",
        "version": "1.0",
        "message": "LinguaListen backend is working normally."
    }




