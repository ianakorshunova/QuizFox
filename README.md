# QuizFox 🦊

QuizFox is a bilingual language-learning and teacher-support app built with Streamlit.

It combines reusable vocabulary sets, multiple quiz modes, AI-generated language practice, and lightweight teacher tools such as a Question Budget and persistent Parking Lot.

## Live demo

Open the demo app on Streamlit:  
[Live Demo](https://quizfox.streamlit.app/)

Demo Mode lets you try quizzes and add temporary vocabulary, but permanent changes are disabled.

## Features

- Manual vocabulary entry
- Bulk vocabulary import
- Adjustable quiz length
- Score tracking
- Practice mistakes mode
- English / Russian interface
- Protected teacher version with Google authentication
- User-specific vocabulary sets
- AI-generated example sentences
- Protected AI usage: public demo responses do not call the OpenAI API
- Saved vocabulary sets
- Load, rename, replace, and delete sets
- Neon/PostgreSQL persistence
- Portfolio Demo Mode with database writes disabled
- Fox reactions during quizzes
- Multiple quiz modes:
  - Multiple Choice
  - Gap Fill
  - Matching
  - Missing Letters with difficulty levels
  - Unscramble
  - Build the Sentence with AI-generated prompts

- Teacher Tools:
  - Question Budget with adjustable tokens
  - Parking Lot for saving lesson questions
  - Resolve and delete parked questions

## Demo Mode

The public portfolio version runs in Demo Mode.

Users can:

- load curated demo vocabulary sets
- add temporary vocabulary
- try all quiz modes
- practice mistakes
- preview AI-powered features using pre-generated examples

Permanent database changes are disabled, and the public demo does not make live OpenAI API requests.

## Tech Stack

- Python
- Streamlit
- Neon / PostgreSQL
- psycopg
- OpenAI API
- Google OAuth / OIDC
- Authlib
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

The protected teacher version uses additional OpenAI API and Google OAuth credentials and is not publicly distributed.

## Status

QuizFox is a portfolio project and is currently under active development.



