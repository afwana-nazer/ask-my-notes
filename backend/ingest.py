
# ingest.py - Reads PDF files and saves their text in ChromaDB

import os
import chromadb
from pypdf import PdfReader


# 1. Create the ChromaDB database
client = chromadb.PersistentClient(path="notes_db")

# 2. Create or connect to the collection
collection = client.get_or_create_collection("my_notes")


# 3. Split text into smaller pieces
def cut_into_pieces(text, size=800, overlap=100):

    pieces = []
    start = 0

    while start < len(text):
        piece = text[start:start + size]

        if piece.strip():
            pieces.append(piece)

        start = start + size - overlap

    return pieces


# 4. Read PDF and add its text to ChromaDB
def add_pdf(path):

    name = os.path.basename(path)

    reader = PdfReader(path)

    count = 0

    print(f"\nReading PDF: {name}")

    # Read each page
    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text() or ""

        # Display extracted text information
        print(
            f"Page {page_number}: "
            f"{len(text)} characters extracted"
        )

        # Split page text into smaller pieces
        pieces = cut_into_pieces(text)

        # Save each piece in ChromaDB
        for i, piece in enumerate(pieces):

            collection.upsert(
                ids=[f"{name}-page{page_number}-{i}"],

                documents=[piece],

                metadatas=[
                    {
                        "source": name,
                        "page": page_number
                    }
                ]
            )

            count += 1

    print(f"\nAdded {name}: {count} pieces")

    if count == 0:
        print(
            "WARNING: No text was extracted. "
            "This PDF may contain scanned images."
        )

    return count


# 5. Run this file directly to add all PDFs from docs folder
if __name__ == "__main__":

    os.makedirs("docs", exist_ok=True)

    for file in os.listdir("docs"):

        if file.lower().endswith(".pdf"):

            add_pdf(os.path.join("docs", file))

    print(
        "\nTotal pieces in the notes box:",
        collection.count()
    )
