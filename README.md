# QuizFox 🦊

QuizFox is a Streamlit vocabulary quiz app designed for quick language-learning practice.

It allows users to create vocabulary sets, run different quiz types, review mistakes, and save reusable sets in a Neon/PostgreSQL database.

## Features

- Manual vocabulary entry
- Bulk vocabulary import
- Multiple Choice quizzes
- Gap Fill quizzes in both directions
- Matching exercises
- Adjustable quiz length
- Score tracking
- Practice mistakes mode
- Saved vocabulary sets
- Load, rename, replace, and delete sets
- Neon/PostgreSQL persistence
- Portfolio Demo Mode with database writes disabled
- Fox reactions during quizzes

## Demo Mode

The public portfolio version runs in Demo Mode.

Users can:
- load existing vocabulary sets
- add temporary vocabulary
- try all quiz modes
- practice mistakes

Permanent database changes such as saving, replacing, renaming, or deleting sets are disabled.

## Tech Stack

- Python
- Streamlit
- Neon / PostgreSQL
- psycopg
- HTML / CSS

## Local Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create:

```text
.streamlit/secrets.toml
```

Add:

```toml
NEON_DATABASE_URL = "your_database_connection_string"
APP_MODE = "owner"
```

Then run:

```bash
streamlit run app.py
```

## Status

QuizFox is a portfolio project and is currently under active development.



