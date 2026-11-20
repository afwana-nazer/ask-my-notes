
# main.py - Backend for Ask My Notes

import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

from ingest import collection, add_pdf


# Read the .env file
load_dotenv()

# Connect to Groq AI
ai = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Create FastAPI application
app = FastAPI()


# Allow React frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Question format
class Question(BaseModel):
    question: str


# Home route
@app.get("/")
def home():
    return {
        "status": "running",
        "pieces": collection.count()
    }


# Ask questions about notes
@app.post("/ask")
def ask(q: Question):

    # 1. Find the 4 most relevant pieces of notes
    results = collection.query(
        query_texts=[q.question],
        n_results=4
    )

    pieces = results["documents"][0]
    sources = results["metadatas"][0]

    # 2. Combine the notes
    notes = "\n\n".join(pieces)

    prompt = f"""Answer the question using ONLY these notes.
If the answer is not in the notes, say "Not found in your notes."

Notes:
{notes}

Question: {q.question}"""

    # 3. Send the question and notes to Groq AI
    reply = ai.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )

    answer = reply.choices[0].message.content

    return {
        "answer": answer,
        "sources": sources
    }


# Upload a PDF from the frontend
@app.post("/upload")
def upload(file: UploadFile = File(...)):

    # Check that the uploaded file is a PDF
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file."
        )

    # Get only the filename
    name = os.path.basename(file.filename)

    # Create docs folder if it does not exist
    os.makedirs("docs", exist_ok=True)

    # Save the PDF inside backend/docs
    path = os.path.join("docs", name)

    try:
        # Save uploaded PDF
        with open(path, "wb") as f:
            f.write(file.file.read())

        # Read PDF and add its contents to ChromaDB
        count = add_pdf(path)

        return {
            "message": f"Added {name} ({count} pieces). Ask me!"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF upload failed: {str(e)}"
        )

    finally:
        file.file.close()
