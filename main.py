# main.py — Backend FastAPI prêt pour Render
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import sqlite3
import csv
import io
import random
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Flashcard(BaseModel):
    id: int = None
    course: str
    chapter: str
    notion: str
    question: str
    answer: str
    score: int = 0


class ReviewInput(BaseModel):
    correct: bool


DB_PATH = os.getenv("DB_PATH", "flashcards.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute(
    """CREATE TABLE IF NOT EXISTS flashcards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course TEXT,
    chapter TEXT,
    notion TEXT,
    question TEXT,
    answer TEXT,
    score INTEGER DEFAULT 0
)"""
)
conn.commit()


@app.get("/api/cards", response_model=List[Flashcard])
def get_cards():
    c.execute("SELECT * FROM flashcards")
    rows = c.fetchall()
    return [
        Flashcard(
            id=row[0],
            course=row[1],
            chapter=row[2],
            notion=row[3],
            question=row[4],
            answer=row[5],
            score=row[6],
        )
        for row in rows
    ]


@app.post("/api/cards", response_model=Flashcard)
def create_card(card: Flashcard):
    c.execute(
        "INSERT INTO flashcards (course, chapter, notion, question, answer, score) VALUES (?, ?, ?, ?, ?, ?)",
        (
            card.course,
            card.chapter,
            card.notion,
            card.question,
            card.answer,
            card.score,
        ),
    )
    conn.commit()
    card.id = c.lastrowid
    return card


@app.put("/api/cards/{card_id}", response_model=Flashcard)
def update_card(card_id: int, card: Flashcard):
    c.execute(
        "UPDATE flashcards SET course = ?, chapter = ?, notion = ?, question = ?, answer = ?, score = ? WHERE id = ?",
        (
            card.course,
            card.chapter,
            card.notion,
            card.question,
            card.answer,
            card.score,
            card_id,
        ),
    )
    conn.commit()
    return card


@app.delete("/api/cards/{card_id}")
def delete_card(card_id: int):
    c.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()
    return {"message": "Carte supprimée"}


@app.post("/api/upload")
def upload_csv(file: UploadFile = File(...)):
    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        c.execute(
            "INSERT INTO flashcards (course, chapter, notion, question, answer, score) VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["Course"],
                row["Chapter"],
                row["Notion"],
                row["Question"],
                row["Answer"],
                int(row.get("Score", 0)),
            ),
        )
    conn.commit()
    return {"message": "Importation réussie"}


@app.post("/api/cards/{card_id}/review")
def review_card(card_id: int, input: ReviewInput):
    correct = input.correct
    c.execute("SELECT score FROM flashcards WHERE id = ?", (card_id,))
    result = c.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Carte non trouvée")
    new_score = max(0, result[0] + (1 if correct else -1))
    c.execute("UPDATE flashcards SET score = ? WHERE id = ?", (new_score, card_id))
    conn.commit()
    return {"id": card_id, "new_score": new_score}


@app.get("/api/review", response_model=Flashcard)
def get_card_to_review():
    c.execute("SELECT * FROM flashcards ORDER BY score ASC")
    rows = c.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucune carte disponible")
    lowest_score_cards = [row for row in rows if row[6] == rows[0][6]]
    selected = random.choice(lowest_score_cards)
    return Flashcard(
        id=selected[0],
        course=selected[1],
        chapter=selected[2],
        notion=selected[3],
        question=selected[4],
        answer=selected[5],
        score=selected[6],
    )
