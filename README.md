# AskDB.Ai

Query any SQLite database in plain English. AskDB.Ai translates natural language into SQL using an LLM, runs the query, and presents the results with auto-generated charts and insights — all inside a clean, Apple-style dark UI.

---

## Features

- **Natural language to SQL** — ask questions in plain English, get answers from your database
- **Auto charts** — results with two columns automatically render as interactive pie or bar charts
- **Schema browser** — explore your database tables and columns in the floating side panel
- **Query history** — click any past question to jump back to it in the chat
- **Data quality profiling** — profile tables to detect nulls, duplicates, and outliers
- **Multi-database support** — connect and switch between multiple SQLite databases

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| LLM | Google Gemini |
| Database | SQLite |

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/Shritin15/AskDB.Ai.git
cd AskDB.Ai
```

### 2. Set up Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Add your Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

### 4. Start the FastAPI backend

```bash
uvicorn api:app --reload
```

The API runs at `http://localhost:8000`.

### 5. Start the React frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Project Structure

```
AskDB.Ai/
├── api.py                  # FastAPI backend
├── llm/
│   ├── client.py           # Gemini LLM client
│   ├── nl_to_sql_service.py
│   ├── insight_service.py
│   └── prompts.py
├── db/
│   ├── schema_introspector.py
│   ├── embedder.py         # Sentence-transformer embeddings
│   └── pruner.py           # Schema token optimisation
├── data_quality/
│   └── profiler.py
├── frontend/
│   └── src/
│       ├── App.jsx
│       └── App.css
└── data/
    └── datasets/
        └── chinook.sqlite
```

---

## Running Tests

```bash
pytest -q
```
