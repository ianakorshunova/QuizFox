import streamlit as st
import random
import re
from pathlib import Path
import base64
import json
import psycopg
import os
from openai import OpenAI

database_url = st.secrets["NEON_DATABASE_URL"]

APP_MODE = os.getenv(
    "QUIZFOX_APP_MODE",
    st.secrets.get("APP_MODE", "demo")
)

def t(key):
    return translations[st.session_state.language][key]

DEMO_MODE = APP_MODE == "demo"

def load_css(file_name):
    with open(file_name, "r") as f:
        st.markdown(
            f"<style>{f.read()}</style>",
            unsafe_allow_html=True
        )

load_css("style.css")

FOX_NEUTRAL = Path(__file__).parent / "pictures" / "fox_neutral.png"
FOX_THINKING = Path(__file__).parent / "pictures" / "fox_thinking.png"
FOX_SNEAKY = Path(__file__).parent / "pictures" / "fox_sneaky.png"

def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

fox_header_b64 = get_image_base64(FOX_NEUTRAL)
fox_thinking_b64 = get_image_base64(FOX_THINKING)
fox_sneaky_b64 = get_image_base64(FOX_SNEAKY)

def show_quiz_fox(image_b64):
    st.markdown(
        f"""
        <div style="display:flex; justify-content:center; margin: 10px 0 20px 0;">
            <img
                src="data:image/png;base64,{image_b64}"
                style="width:140px; height:auto; border-radius:20px;"
            >
        </div>
        """,
        unsafe_allow_html=True
    )

def save_set_to_db(set_name, vocabulary):
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vocabulary_sets (name)
                VALUES (%s)
                RETURNING id;
                """,
                (set_name,)
            )

            set_id = cur.fetchone()[0]

            for item in vocabulary:
                cur.execute(
                    """
                    INSERT INTO vocabulary_items (
                        set_id,
                        word,
                        translation
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (
                        set_id,
                        item["word"],
                        item["translation"]
                    )
                )

        conn.commit()

def replace_set_in_db(set_name, vocabulary):
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id
                FROM vocabulary_sets
                WHERE name = %s;
                """,
                (set_name,)
            )

            row = cur.fetchone()

            if row is None:
                return

            set_id = row[0]

            cur.execute(
                """
                DELETE FROM vocabulary_items
                WHERE set_id = %s;
                """,
                (set_id,)
            )

            for item in vocabulary:
                cur.execute(
                    """
                    INSERT INTO vocabulary_items (
                        set_id,
                        word,
                        translation
                    )
                    VALUES (%s, %s, %s);
                    """,
                    (
                        set_id,
                        item["word"],
                        item["translation"]
                    )
                )

        conn.commit()

def rename_set_in_db(old_name, new_name):
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE vocabulary_sets
                SET name = %s
                WHERE name = %s;
                """,
                (
                    new_name,
                    old_name
                )
            )

        conn.commit()

def delete_set_from_db(set_name):
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM vocabulary_sets
                WHERE name = %s;
                """,
                (set_name,)
            )

        conn.commit()

def load_sets_from_db():
    sets = {}

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    vs.id,
                    vs.name,
                    vi.word,
                    vi.translation
                FROM vocabulary_sets AS vs
                LEFT JOIN vocabulary_items AS vi
                    ON vi.set_id = vs.id
                ORDER BY vs.id, vi.id;
                """
            )

            rows = cur.fetchall()

    for set_id, set_name, word, translation in rows:
        if set_name not in sets:
            sets[set_name] = []

        if word is not None:
            sets[set_name].append(
                {
                    "word": word,
                    "translation": translation
                }
            )

    return sets

correct_reactions = [
    "correct_1",
    "correct_2",
    "correct_3",
    "correct_4",
    "correct_5",
]

wrong_reactions = [
    "wrong_1",
    "wrong_2",
    "wrong_3",
    "wrong_4",
    "wrong_5",
]

st.set_page_config(
    page_title="QuizFox",
    page_icon="🦊",
    layout="centered"
)

def create_question(correct_item):
    wrong_items = [
        item
        for item in st.session_state.vocabulary
        if item != correct_item
    ]

    distractors = random.sample(wrong_items, 3)

    options = [
        correct_item["translation"],
        distractors[0]["translation"],
        distractors[1]["translation"],
        distractors[2]["translation"]
    ]

    random.shuffle(options)

    return {
        "word": correct_item["word"],
        "correct_answer": correct_item["translation"],
        "options": options
    }

def format_word_count(count):
    if st.session_state.language == "en":
        return f"{count} word" if count == 1 else f"{count} words"

    if 11 <= count % 100 <= 14:
        form = "слов"
    elif count % 10 == 1:
        form = "слово"
    elif 2 <= count % 10 <= 4:
        form = "слова"
    else:
        form = "слов"

    return f"{count} {form}"

translations = {
    "en": {
        "navigation": "Navigation",
        "vocabulary": "Vocabulary",
        "quiz": "Quiz",

        "add_vocabulary": "Add vocabulary",
        "paste_vocabulary": (
            "Paste vocabulary "
            "(one pair per line; use a tab, —, or 2+ spaces):"
        ),
        "import_vocabulary": "Import vocabulary",
        "word": "Word",
        "translation": "Translation",
        "add_word": "Add word",
        "vocabulary_set": "Vocabulary set",
        "clear_vocabulary": "Clear vocabulary",
        "saved_sets": "Saved sets",
        "set_name": "Set name",
        "save_set": "Save set",
        "your_saved_sets": "Your saved sets",
        "choose_set": "Choose a set",
        "load_set": "Load set",
        "rename_set": "Rename set",
        "delete_set": "Delete set",
        "add_vocabulary": "Add vocabulary",
        "import_vocabulary": "Import vocabulary",
        "paste_vocabulary": (
            "Paste vocabulary "
            "(one pair per line; use a tab, —, or 2+ spaces):"
        ),
        "import_button": "Import vocabulary",
        "all_words_exist": "All these words are already in the vocabulary set.",
        "no_valid_pairs": "No valid vocabulary pairs found.",
        "word": "Word",
        "translation": "Translation",
        "add_word": "Add word",
        "enter_both": "Please enter both the word and the translation.",
        "imported_words": "Imported {count} new words.",
        "added_word": "Added: {word} — {translation}",
        "vocabulary_set": "Vocabulary set",
        "clear_vocabulary": "Clear vocabulary",
        "edit": "Edit",
        "delete": "Delete",
        "save_changes": "Save changes",
        "cancel": "Cancel",
        "pair_exists": "This vocabulary pair already exists.",
        "empty_word_translation": "Word and translation cannot be empty.",
        "saved_sets": "Saved sets",
        "set_name": "Set name",
        "set_name_placeholder": "e.g. Nature A2",
        "save_set": "Save set",
        "enter_set_name": "Enter a set name first.",
        "add_vocabulary_first": "Add some vocabulary first.",
        "set_saved": 'Set "{name}" saved!',
        "set_exists_replace": 'Set "{name}" already exists. Replace it?',
        "yes_replace": "Yes, replace",
        "cancel_replace": "Cancel replace",
        "your_saved_sets": "Your saved sets",
        "choose_set": "Choose a set",
        "words_count": "{count} words",
        "load_set": "Load set",
        "set_loaded": 'Set "{name}" loaded!',
        "delete_set": "Delete set",
        "delete_set_confirm": 'Delete set "{name}"?',
        "yes_delete": "Yes, delete",
        "cancel": "Cancel",
        "rename_set": "Rename set",
        "new_set_name": "New set name",
        "save_new_name": "Save new name",
        "set_name_empty": "Set name cannot be empty.",
        "set_name_exists": "A set with this name already exists.",
        "cancel_rename": "Cancel rename",
        "quiz_title": "Quiz",
        "score": "Score",
        "add_4_words": "Add at least 4 words to generate a quiz.",
        "number_questions": "Number of questions:",
        "quiz_type": "Quiz type:",
        "multiple_choice": "Multiple Choice",
        "gap_fill": "Gap Fill",
        "matching": "Matching",
        "gap_direction": "Gap Fill direction:",
        "translation_to_word": "Translation → Word",
        "word_to_translation": "Word → Translation",
        "start_quiz": "Start quiz",
        "match_words": "Match the words",
        "check_matches": "Check matches",
        "correct_answer": "correct",
        "matching_score": "Matching score",
        "perfect_match": "🦊 Perfect match!",
        "nice_work": "🦊 Nice work!",
        "keep_going": "🦊 Keep going!",
        "next_matching_round": "Next matching round",
        "end_quiz": "End quiz",
        "question_progress": "Question {current} of {total}",
        "what_does_mean": 'What does "{word}" mean?',
        "choose_answer": "Choose an answer:",
        "translate_prompt": 'Translate "{text}"',
        "your_answer": "Your answer:",
        "check_answer": "Check answer",
        "enter_answer_first": "Enter an answer first.",
        "correct_answer_is": "The correct answer is: {answer}",
        "next_question": "Next question",
        "end_quiz": "End quiz",
        "quiz_complete": "Quiz complete! 🦊",
        "final_score": "Final score",
        "percent_correct": "{percentage}% correct",
        "questions_completed": "Questions completed",
        "practice_mistakes": "Practice mistakes",
        "start_new_quiz": "Start new quiz",
        "correct_1": "🦊 Correct!",
        "correct_2": "🦊 Fox-approved!",
        "correct_3": "🦊 Nice one!",
        "correct_4": "🦊 Nailed it!",
        "correct_5": "🦊 The fox is impressed.",

        "wrong_1": "🦊 Almost!",
        "wrong_2": "🦊 Sneaky question!",
        "wrong_3": "🦊 Not this time!",
        "wrong_4": "🦊 The fox demands another attempt.",
        "wrong_5": "🦊 So close!",

        "demo_mode_banner": (
            "Portfolio demo — database changes are disabled. "
            "You can add vocabulary and try quizzes, but changes won’t be saved."
        ),

        "ai_fox_assistant": "🦊 AI Fox Assistant",
        "ai_fox_coming_soon": "AI features will appear here soon.",

        "choose_word_for_ai": "Choose a word:",
        "generate_example": "Generate example",

        "ai_owner_placeholder": "Live AI generation will be connected here.",

        "ai_demo_note": (
            "Demo mode — try a sample pre-generated AI response."
        ),

        "ai_fox_title": "🦊 AI Fox Assistant",
        "ai_thinking": "The fox is thinking...",
        "ai_key_missing": "OpenAI API is not connected yet.",
        "ai_error": "Something went wrong while generating the example.",
    },

    "ru": {
        "navigation": "Навигация",
        "vocabulary": "Словарь",
        "quiz": "Квиз",

        "add_vocabulary": "Добавить слова",
        "paste_vocabulary": (
            "Вставьте слова "
            "(одна пара на строку; используйте табуляцию, — или 2+ пробела):"
        ),
        "import_vocabulary": "Импортировать слова",
        "word": "Слово",
        "translation": "Перевод",
        "add_word": "Добавить слово",
        "vocabulary_set": "Текущий набор",
        "clear_vocabulary": "Очистить словарь",
        "saved_sets": "Сохранённые наборы",
        "set_name": "Название набора",
        "save_set": "Сохранить набор",
        "your_saved_sets": "Ваши сохранённые наборы",
        "choose_set": "Выберите набор",
        "load_set": "Загрузить набор",
        "rename_set": "Переименовать набор",
        "delete_set": "Удалить набор",
         "add_vocabulary": "Добавить слова",
        "import_vocabulary": "Импорт слов",
        "paste_vocabulary": (
            "Вставьте слова "
            "(одна пара на строку; используйте табуляцию, — или 2+ пробела):"
        ),
        "import_button": "Импортировать слова",
        "all_words_exist": "Все эти слова уже есть в текущем наборе.",
        "no_valid_pairs": "Не найдено корректных пар слов.",
        "word": "Слово",
        "translation": "Перевод",
        "add_word": "Добавить слово",
        "enter_both": "Введите слово и перевод.",
        "imported_words": "Добавлено новых слов: {count}.",
        "added_word": "Добавлено: {word} — {translation}",
        "vocabulary_set": "Текущий набор",
        "clear_vocabulary": "Очистить словарь",
        "edit": "Изменить",
        "delete": "Удалить",
        "save_changes": "Сохранить изменения",
        "cancel": "Отмена",
        "pair_exists": "Такая пара уже есть в словаре.",
        "empty_word_translation": "Слово и перевод не могут быть пустыми.",
        "saved_sets": "Сохранённые наборы",
        "set_name": "Название набора",
        "set_name_placeholder": "например, Природа A2",
        "save_set": "Сохранить набор",
        "enter_set_name": "Введите название набора.",
        "add_vocabulary_first": "Сначала добавьте слова.",
        "set_saved": 'Набор «{name}» сохранён!',
        "set_exists_replace": 'Набор «{name}» уже существует. Заменить его?',
        "yes_replace": "Да, заменить",
        "cancel_replace": "Отмена",
        "your_saved_sets": "Ваши сохранённые наборы",
        "choose_set": "Выберите набор",
        "words_count": "{count} слов",
        "load_set": "Загрузить набор",
        "set_loaded": 'Набор «{name}» загружен!',
        "delete_set": "Удалить набор",
        "delete_set_confirm": 'Удалить набор «{name}»?',
        "yes_delete": "Да, удалить",
        "cancel": "Отмена",
        "rename_set": "Переименовать набор",
        "new_set_name": "Новое название набора",
        "save_new_name": "Сохранить новое название",
        "set_name_empty": "Название набора не может быть пустым.",
        "set_name_exists": "Набор с таким названием уже существует.",
        "cancel_rename": "Отменить переименование",
        "quiz_title": "Квиз",
        "score": "Счёт",
        "add_4_words": "Добавьте хотя бы 4 слова, чтобы создать квиз.",
        "number_questions": "Количество вопросов:",
        "quiz_type": "Тип задания:",
        "multiple_choice": "Выбор ответа",
        "gap_fill": "Заполнить пропуск",
        "matching": "Сопоставление",
        "gap_direction": "Направление:",
        "translation_to_word": "Перевод → Слово",
        "word_to_translation": "Слово → Перевод",
        "start_quiz": "Начать квиз",
        "match_words": "Сопоставьте слова",
        "check_matches": "Проверить",
        "correct_answer": "правильно",
        "matching_score": "Результат сопоставления",
        "perfect_match": "🦊 Идеально!",
        "nice_work": "🦊 Отличная работа!",
        "keep_going": "🦊 Продолжайте!",
        "next_matching_round": "Следующий раунд",
        "end_quiz": "Завершить квиз",
        "question_progress": "Вопрос {current} из {total}",
        "what_does_mean": 'Что означает «{word}»?',
        "choose_answer": "Выберите ответ:",
        "translate_prompt": 'Переведите «{text}»',
        "your_answer": "Ваш ответ:",
        "check_answer": "Проверить ответ",
        "enter_answer_first": "Сначала введите ответ.",
        "correct_answer_is": "Правильный ответ: {answer}",
        "next_question": "Следующий вопрос",
        "end_quiz": "Завершить квиз",
        "quiz_complete": "Квиз завершён! 🦊",
        "final_score": "Итоговый счёт",
        "percent_correct": "Правильных ответов: {percentage}%",
        "questions_completed": "Выполнено вопросов",
        "practice_mistakes": "Повторить ошибки",
        "start_new_quiz": "Начать новый квиз",
        "correct_1": "🦊 Правильно!",
        "correct_2": "🦊 Лис одобряет!",
        "correct_3": "🦊 Отлично!",
        "correct_4": "🦊 Точно в цель!",
        "correct_5": "🦊 Лис впечатлён.",

        "wrong_1": "🦊 Почти!",
        "wrong_2": "🦊 Коварный вопрос!",
        "wrong_3": "🦊 В этот раз не вышло!",
        "wrong_4": "🦊 Лис требует ещё одну попытку.",
        "wrong_5": "🦊 Совсем близко!",

        "demo_mode_banner": (
            "Демо для портфолио — изменения в базе данных отключены. "
            "Вы можете добавлять слова и проходить квизы, но изменения не сохранятся."
        ),

        "ai_fox_assistant": "🦊 Лис-ассистент",
        "ai_fox_coming_soon": "ИИ-функции скоро появятся здесь.",

        "choose_word_for_ai": "Выберите слово:",
        "generate_example": "Сгенерировать пример",

        "ai_owner_placeholder": "Здесь будет подключена генерация с помощью ИИ.",

        "ai_demo_note": (
            "Демо-режим — попробуйте пример заранее подготовленного ИИ-ответа."
        ),

        "ai_fox_title": "🦊 Лис-ассистент",
        "ai_thinking": "Лис думает...",
        "ai_key_missing": "OpenAI API пока не подключён.",
        "ai_error": "Не удалось сгенерировать пример.",
    },
}

def t(key):
    return translations[st.session_state.language][key]

DEMO_AI_EXAMPLES = [
    "Why is the elephant so huge?",
    "My brother doesn't like swimming in the sea.",
    "你几点上班？",
]

def generate_ai_example(word, translation):
    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )

    word_history = st.session_state.ai_example_history.get(
        word,
        []
    )

    previous_examples = "\n".join(
        word_history[-5:]
    )

    response = client.responses.create(
        model="gpt-5.2",
        temperature=1.1,
        input=(
            "Create one short, natural example sentence "
            f"using the vocabulary item '{word}'. "
            f"Its translation is '{translation}'. "
            "Write the sentence in the same language as the vocabulary item. "
            "Make the example varied and specific. "
            "Avoid generic textbook patterns. "
            "Do not repeat the same setting, subject, verb, situation, "
            "or sentence structure used in recent examples. "
            "Use different contexts such as daily life, work, travel, family, "
            "nature, hobbies, questions, plans, opinions, or unexpected situations. "
            "\n\nRecent examples to avoid resembling:\n"
            f"{previous_examples}"
            "\n\nReturn only the example sentence."
        ),
    )

    example = response.output_text

    st.session_state.ai_example_history.setdefault(
        word,
        []
    ).append(example)

    return example

@st.dialog("🦊 AI Fox Assistant")
def show_ai_fox_dialog():
    st.subheader(t("ai_fox_title"))

    if DEMO_MODE:
        st.caption(t("ai_demo_note"))

        if st.button(t("generate_example")):
            example = random.choice(DEMO_AI_EXAMPLES)
            st.write(example)

    else:
        if not st.session_state.vocabulary:
            st.info(t("add_vocabulary_first"))
            return

        selected_word = st.selectbox(
            t("choose_word_for_ai"),
            st.session_state.vocabulary,
            format_func=lambda item: (
                f"{item['word']} — {item['translation']}"
            )
        )

        if st.button(t("generate_example")):
            if "OPENAI_API_KEY" not in st.secrets:
                st.info(t("ai_key_missing"))
            else:
                with st.spinner(t("ai_thinking")):
                    try:
                        example = generate_ai_example(
                            selected_word["word"],
                            selected_word["translation"]
                        )

                        st.success(example)

                    except Exception:
                        st.error(t("ai_error"))

language_label = st.sidebar.selectbox(
    "Language",
    ["English", "Русский"]
)

st.session_state.language = (
    "ru" if language_label == "Русский" else "en"
)

page = st.sidebar.radio(
    t("navigation"),
    ["vocabulary", "quiz"],
    format_func=lambda option: t(option)
)

if DEMO_MODE:
    st.info(t("demo_mode_banner"))
# -------------------------
# Session state
# -------------------------

if "vocabulary" not in st.session_state:
    st.session_state.vocabulary = []

if "quiz_question" not in st.session_state:
    st.session_state.quiz_question = None

if "score" not in st.session_state:
    st.session_state.score = 0

if "total_questions" not in st.session_state:
    st.session_state.total_questions = 0

if "answered" not in st.session_state:
    st.session_state.answered = False

if "reaction" not in st.session_state:
    st.session_state.reaction = None

if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

if "quiz_finished" not in st.session_state:
    st.session_state.quiz_finished = False

if "quiz_length" not in st.session_state:
    st.session_state.quiz_length = 5

if "quiz_words" not in st.session_state:
    st.session_state.quiz_words = []

if "editing_word_index" not in st.session_state:
    st.session_state.editing_word_index = None

if "quiz_type" not in st.session_state:
    st.session_state.quiz_type = "Multiple Choice"

if "answer_key_counter" not in st.session_state:
    st.session_state.answer_key_counter = 0

if "gap_direction" not in st.session_state:
    st.session_state.gap_direction = "Translation → Word"

if "matching_pairs" not in st.session_state:
    st.session_state.matching_pairs = []

if "matching_answers" not in st.session_state:
    st.session_state.matching_answers = {}

if "matching_checked" not in st.session_state:
    st.session_state.matching_checked = False

if "matching_options" not in st.session_state:
    st.session_state.matching_options = []

if "matching_round_counter" not in st.session_state:
    st.session_state.matching_round_counter = 0

if "matching_round_score" not in st.session_state:
    st.session_state.matching_round_score = 0

if "mistake_words" not in st.session_state:
    st.session_state.mistake_words = []

if "retry_mode" not in st.session_state:
    st.session_state.retry_mode = False

if "confirm_delete_set" not in st.session_state:
    st.session_state.confirm_delete_set = False

if "delete_set_name" not in st.session_state:
    st.session_state.delete_set_name = None

if "renaming_set" not in st.session_state:
    st.session_state.renaming_set = False

if "rename_set_name" not in st.session_state:
    st.session_state.rename_set_name = None

if "clear_add_form" not in st.session_state:
    st.session_state.clear_add_form = False

if "added_message" not in st.session_state:
    st.session_state.added_message = None

if "confirm_replace_set" not in st.session_state:
    st.session_state.confirm_replace_set = False

if "replace_set_name" not in st.session_state:
    st.session_state.replace_set_name = None

if "load_message" not in st.session_state:
    st.session_state.load_message = None

if "clear_set_name" not in st.session_state:
    st.session_state.clear_set_name = False

if "save_set_message" not in st.session_state:
    st.session_state.save_set_message = None

if "clear_bulk_vocabulary" not in st.session_state:
    st.session_state.clear_bulk_vocabulary = False

if "import_message" not in st.session_state:
    st.session_state.import_message = None

if "fox_mood" not in st.session_state:
    st.session_state.fox_mood = "neutral"

if "language" not in st.session_state:
    st.session_state.language = "en"

if "ai_example_history" not in st.session_state:
    st.session_state.ai_example_history = {}

all_sets = load_sets_from_db()

if DEMO_MODE:
    DEMO_SET_NAMES = [
        "English — Animals",
        "English — Nature",
        "Chinese — Daily Life",
        "Chinese — HSK 4",
    ]

    st.session_state.vocabulary_sets = {
        name: words
        for name, words in all_sets.items()
        if name in DEMO_SET_NAMES
    }

else:
    st.session_state.vocabulary_sets = all_sets

st.markdown(
    f"""
    <div class="quizfox-header">
        <img
            src="data:image/png;base64,{fox_header_b64}"
            class="quizfox-header-img"
        >
        <div class="quizfox-header-text">
            <h1>QuizFox</h1>
            <p>Create quick vocabulary quizzes for your students.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Add vocabulary
# -------------------------

if page == "vocabulary":

    st.subheader(t("add_vocabulary"))

    st.subheader(t("import_vocabulary"))

    if st.session_state.clear_bulk_vocabulary:
        st.session_state.bulk_vocabulary_input = ""
        st.session_state.clear_bulk_vocabulary = False

    if st.session_state.import_message:
        st.success(st.session_state.import_message)
        st.session_state.import_message = None

    bulk_vocabulary = st.text_area(
        t("paste_vocabulary"),
        placeholder="forest\tлес\nocean\tокеан\ncity\tгород",
        key="bulk_vocabulary_input"
    )

    if st.button(t("import_button")):
        imported_words = []

        for line in bulk_vocabulary.splitlines():
            line = line.strip()

            if not line:
                continue

            if "\t" in line:
                parts = line.split("\t", 1)

            elif " — " in line:
                parts = line.split(" — ", 1)

            else:
                parts = re.split(r"\s{2,}", line, maxsplit=1)

            if len(parts) == 2:
                word = parts[0].replace("**", "").strip()
                translation = parts[1].replace("**", "").strip()

                if word and translation:
                    imported_words.append(
                        {
                            "word": word,
                            "translation": translation
                        }
                    )

        if imported_words:
            existing_pairs = {
                (
                    item["word"].strip().lower(),
                    item["translation"].strip().lower()
                )
                for item in st.session_state.vocabulary
            }

            new_words = []

            for item in imported_words:
                normalized_pair = (
                    item["word"].strip().lower(),
                    item["translation"].strip().lower()
                )

                if normalized_pair not in existing_pairs:
                    new_words.append(item)
                    existing_pairs.add(normalized_pair)

            if new_words:
                st.session_state.vocabulary.extend(new_words)

                st.session_state.import_message = t(
                    "imported_words"
                ).format(
                    count=len(new_words)
                )

                st.session_state.clear_bulk_vocabulary = True
                st.rerun()

            else:
                st.info(t("all_words_exist"))

        else:
            st.warning(t("no_valid_pairs"))

    if st.session_state.clear_add_form:
        st.session_state.word_input = ""
        st.session_state.translation_input = ""
        st.session_state.clear_add_form = False

    word = st.text_input(
        t("word"),
        key="word_input"
    )

    translation = st.text_input(
        t("translation"),
        key="translation_input"
    )

    if st.button(t("add_word")):
        if word and translation:
            st.session_state.vocabulary.append(
                {
                    "word": word,
                    "translation": translation
                }
            )

            st.session_state.clear_add_form = True
            st.session_state.added_message = t(
                "added_word"
            ).format(
                word=word,
                translation=translation
            )
            st.rerun()

        else:
            st.warning(t("enter_both"))

    if st.session_state.added_message:
        st.success(st.session_state.added_message)
        st.session_state.added_message = None

    # -------------------------
    # Vocabulary list
    # -------------------------

    if st.session_state.load_message:
        st.success(st.session_state.load_message)
        st.session_state.load_message = None

    if st.session_state.vocabulary:
        st.subheader(t("vocabulary_set"))

        if st.button(t("clear_vocabulary")):
            st.session_state.vocabulary = []
            st.session_state.quiz_words = []
            st.session_state.quiz_question = None
            st.session_state.quiz_started = False
            st.session_state.quiz_finished = False
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.session_state.editing_word_index = None
            st.rerun()

        for index, item in enumerate(st.session_state.vocabulary):
            col1, col2, col3 = st.columns([4, 1.4, 1.2])

            with col1:
                st.markdown(
                    f"**{item['word']}** — {item['translation']}"
                )

            with col2:
                if st.button(
                    t("edit"),
                    key=f"edit_word_{index}"
                ):
                    st.session_state.editing_word_index = index
                    st.rerun()

            with col3:
                if st.button(
                    t("delete"),
                    key=f"delete_word_{index}"
                ):
                    st.session_state.vocabulary.pop(index)

                    st.session_state.quiz_words = []
                    st.session_state.quiz_question = None
                    st.session_state.quiz_started = False
                    st.session_state.quiz_finished = False
                    st.session_state.score = 0
                    st.session_state.total_questions = 0
                    st.session_state.editing_word_index = None

                    st.rerun()

            if st.session_state.editing_word_index == index:

                edited_word = st.text_input(
                    t("word"),
                    value=item["word"],
                    key=f"edited_word_{index}"
                )

                edited_translation = st.text_input(
                    t("translation"),
                    value=item["translation"],
                    key=f"edited_translation_{index}"
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    if st.button(
                        t("save_changes"),
                        key=f"save_word_{index}"
                    ):
                        if edited_word.strip() and edited_translation.strip():
                            new_pair = (
                                edited_word.strip().lower(),
                                edited_translation.strip().lower()
                            )

                            other_pairs = {
                                (
                                    vocab_item["word"].strip().lower(),
                                    vocab_item["translation"].strip().lower()
                                )
                                for vocab_index, vocab_item
                                in enumerate(st.session_state.vocabulary)
                                if vocab_index != index
                            }

                            if new_pair in other_pairs:
                                st.warning(
                                    t("pair_exists")
                                )

                            else:
                                st.session_state.vocabulary[index] = {
                                    "word": edited_word.strip(),
                                    "translation": edited_translation.strip()
                                }

                                st.session_state.editing_word_index = None

                                st.session_state.quiz_words = []
                                st.session_state.quiz_question = None
                                st.session_state.quiz_started = False
                                st.session_state.quiz_finished = False
                                st.session_state.score = 0
                                st.session_state.total_questions = 0

                                st.rerun()

                        else:
                            st.warning(
                                t("empty_word_translation")
                            )

                with cancel_col:
                    if st.button(
                        t("cancel"),
                        key=f"cancel_edit_{index}"
                    ):
                        st.session_state.editing_word_index = None
                        st.rerun()

    if st.button(t("ai_fox_assistant")):
        show_ai_fox_dialog()

    st.subheader(t("saved_sets"))

    if st.session_state.save_set_message:
        st.success(st.session_state.save_set_message)
        st.session_state.save_set_message = None

    if st.session_state.clear_set_name:
        st.session_state.set_name_input = ""
        st.session_state.clear_set_name = False

    set_name = st.text_input(
        t("set_name"),
        placeholder=t("set_name_placeholder"),
        key="set_name_input"
    )

    if st.button(
        t("save_set"),
        disabled=DEMO_MODE
    ):
        clean_set_name = set_name.strip()

        if not clean_set_name:
            st.warning(t("enter_set_name"))

        elif not st.session_state.vocabulary:
            st.warning(t("add_vocabulary_first"))

        elif clean_set_name in st.session_state.vocabulary_sets:
            st.session_state.confirm_replace_set = True
            st.session_state.replace_set_name = clean_set_name
            st.rerun()

        else:
            save_set_to_db(
                clean_set_name,
                st.session_state.vocabulary
            )

            st.session_state.vocabulary_sets = load_sets_from_db()

            st.session_state.clear_set_name = True

            st.session_state.save_set_message = (
                t("set_saved").format(name=clean_set_name)
            )

            st.rerun()

    if st.session_state.confirm_replace_set:
        replace_set_name = st.session_state.replace_set_name

        st.warning(
            t("set_exists_replace").format(name=replace_set_name)
        )

        replace_col, cancel_replace_col = st.columns(2)

        with replace_col:
            if st.button(
                t("yes_replace"),
                disabled=DEMO_MODE
            ):
                replace_set_in_db(
                    replace_set_name,
                    st.session_state.vocabulary
                )

                st.session_state.vocabulary_sets = load_sets_from_db()

                st.session_state.confirm_replace_set = False
                st.session_state.replace_set_name = None
                st.rerun()

        with cancel_replace_col:
            if st.button(t("cancel_replace")):
                st.session_state.confirm_replace_set = False
                st.session_state.replace_set_name = None
                st.rerun()

    if st.session_state.vocabulary_sets:
        st.write(f"### {t('your_saved_sets')}")

        selected_set = st.selectbox(
            t("choose_set"),
            list(st.session_state.vocabulary_sets.keys()),
            format_func=lambda name: (
                f"{name} — "
                f"{format_word_count(len(st.session_state.vocabulary_sets[name]))}"
            )
        )

        if st.button(t("load_set")):
            st.session_state.vocabulary = [
                item.copy()
                for item in st.session_state.vocabulary_sets[selected_set]
            ]

            st.session_state.load_message = (
                t("set_loaded").format(name=selected_set)
            )

            st.rerun()

        if not st.session_state.confirm_delete_set:
            if st.button(
                t("delete_set"),
                disabled=DEMO_MODE
            ):
                st.session_state.confirm_delete_set = True
                st.session_state.delete_set_name = selected_set
                st.rerun()

        else:
            delete_set_name = st.session_state.delete_set_name

            st.warning(
                t("delete_set_confirm").format(name=delete_set_name)
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                if st.button(
                    t("yes_delete"),
                    disabled=DEMO_MODE
                ):
                    delete_set_from_db(delete_set_name)

                    st.session_state.vocabulary_sets = load_sets_from_db()

                    st.session_state.confirm_delete_set = False
                    st.session_state.delete_set_name = None
                    st.rerun()

            with cancel_col:
                if st.button(t("cancel")):
                    st.session_state.confirm_delete_set = False
                    st.session_state.delete_set_name = None
                    st.rerun()

        if not st.session_state.renaming_set:
            if st.button(
                t("rename_set"),
                disabled=DEMO_MODE
            ):
                st.session_state.renaming_set = True
                st.session_state.rename_set_name = selected_set
                st.rerun()

        if st.session_state.renaming_set:
            old_name = st.session_state.rename_set_name

            new_name = st.text_input(
                t("new_set_name"),
                value=old_name
            )

            rename_col, cancel_rename_col = st.columns(2)

            with rename_col:
                if st.button(
                    t("save_new_name"),
                    disabled=DEMO_MODE
                ):
                    new_name = new_name.strip()

                    if not new_name:
                        st.warning(t("set_name_empty"))

                    elif (
                        new_name != old_name
                        and new_name in st.session_state.vocabulary_sets
                    ):
                        st.warning(t("set_name_exists"))

                    else:
                        rename_set_in_db(
                            old_name,
                            new_name
                        )

                        st.session_state.vocabulary_sets = load_sets_from_db()

                        st.session_state.renaming_set = False
                        st.session_state.rename_set_name = None
                        st.rerun()

            with cancel_rename_col:
                if st.button(t("cancel_rename")):
                    st.session_state.renaming_set = False
                    st.session_state.rename_set_name = None
                    st.rerun()

# -------------------------
# Quiz
# -------------------------

elif page == "quiz":
    st.divider()
    st.subheader(t("quiz_title"))

    st.write(
        f"🦊 **{t('score')}: {st.session_state.score} / "
        f"{st.session_state.total_questions}**"
    )

    if len(st.session_state.vocabulary) < 4:
        st.info(t("add_4_words"))

    else:
        if (
            not st.session_state.quiz_started
            and not st.session_state.quiz_finished
        ):

            max_questions = min(len(st.session_state.vocabulary), 15)

            quiz_options = [
                number
                for number in [5, 10, 15]
                if number <= max_questions
            ]

            if max_questions not in quiz_options:
                quiz_options.append(max_questions)

            quiz_options.sort()

            quiz_length = st.radio(
                t("number_questions"),
                quiz_options,
                horizontal=True
            )

            quiz_type = st.radio(
                t("quiz_type"),
                [
                    "multiple_choice",
                    "gap_fill",
                    "matching"
                ],
                format_func=lambda option: t(option),
                horizontal=True
            )

            if quiz_type == "gap_fill":
                gap_direction = st.radio(
                    t("gap_direction"),
                    [
                        "translation_to_word",
                        "word_to_translation"
                    ],
                    format_func=lambda option: t(option),
                    horizontal=True
                )

            if st.button(t("start_quiz")):
                st.session_state.mistake_words = []
                st.session_state.retry_mode = False
                st.session_state.quiz_type = quiz_type
                st.session_state.score = 0
                st.session_state.total_questions = 0
                st.session_state.reaction = None
                st.session_state.quiz_finished = False
                st.session_state.quiz_length = quiz_length
                st.session_state.answer_key_counter += 1

                if quiz_type == "matching":
                    matching_count = min(4, len(st.session_state.vocabulary))
                    st.session_state.matching_round_counter += 1

                    st.session_state.matching_pairs = random.sample(
                        st.session_state.vocabulary,
                        matching_count
                    )

                    st.session_state.matching_options = [
                        item["translation"]
                        for item in st.session_state.matching_pairs
                    ]

                    random.shuffle(st.session_state.matching_options)

                    st.session_state.matching_answers = {}
                    st.session_state.matching_checked = False

                    st.session_state.quiz_question = None
                    st.session_state.quiz_words = []

                else:
                    st.session_state.quiz_words = random.sample(
                        st.session_state.vocabulary,
                        st.session_state.quiz_length
                    )

                    correct_item = st.session_state.quiz_words[0]

                    st.session_state.quiz_question = create_question(
                        correct_item
                    )

                st.session_state.quiz_started = True
                st.session_state.answered = False

                st.rerun()

    # -------------------------
    # Show quiz question
    # -------------------------

    if (
        st.session_state.quiz_started
        and not st.session_state.quiz_finished
    ):

        if not st.session_state.answered:
            show_quiz_fox(fox_thinking_b64)
        else:
            show_quiz_fox(fox_sneaky_b64)
        
        if st.session_state.quiz_type == "matching":
            st.subheader(t("match_words"))

            for index, item in enumerate(st.session_state.matching_pairs):
                selected_translation = st.selectbox(
                    f"{item['word']}",
                    [""] + st.session_state.matching_options,
                    key=(
                        f"matching_answer_"
                        f"{st.session_state.matching_round_counter}_"
                        f"{index}"
                    )
                )

                st.session_state.matching_answers[index] = selected_translation

            if not st.session_state.matching_checked:
                if st.button(t("check_matches")):
                    matching_score = 0

                    for index, item in enumerate(st.session_state.matching_pairs):
                        selected_translation = st.session_state.matching_answers.get(
                            index,
                            ""
                        )

                        if selected_translation == item["translation"]:
                            matching_score += 1

                    st.session_state.matching_round_score = matching_score

                    st.session_state.score += matching_score
                    st.session_state.total_questions += len(
                        st.session_state.matching_pairs
                    )

                    st.session_state.matching_checked = True
                    st.rerun()

            else:
                matching_score = st.session_state.matching_round_score

                for index, item in enumerate(st.session_state.matching_pairs):
                    selected_translation = st.session_state.matching_answers.get(
                        index,
                        ""
                    )

                    if selected_translation == item["translation"]:
                        st.success(
                            f"{item['word']} — {item['translation']}"
                        )
                    else:
                        st.error(
                            f"{item['word']} — {t('correct_answer')}: "
                            f"{item['translation']}"
                        )

                st.write(
                    f"### {t('matching_score')}: "
                    f"{matching_score} / {len(st.session_state.matching_pairs)}"
                )

                if matching_score == len(st.session_state.matching_pairs):
                    st.success(t("perfect_match"))

                elif matching_score >= len(st.session_state.matching_pairs) / 2:
                    st.info(t("nice_work"))

                else:
                    st.error(t("keep_going"))

                if st.button(t("next_matching_round")):
                    st.session_state.matching_round_score = 0

                    matching_count = min(
                        4,
                        len(st.session_state.vocabulary)
                    )

                    st.session_state.matching_pairs = random.sample(
                        st.session_state.vocabulary,
                        matching_count
                    )

                    st.session_state.matching_options = [
                        item["translation"]
                        for item in st.session_state.matching_pairs
                    ]

                    random.shuffle(
                        st.session_state.matching_options
                    )

                    st.session_state.matching_answers = {}
                    st.session_state.matching_checked = False
                    st.session_state.matching_round_counter += 1

                    st.rerun()

                if st.button(
                    t("end_quiz"),
                    key="end_matching_quiz"
                ):
                    st.session_state.quiz_finished = True
                    st.rerun()

        else:
            question = st.session_state.quiz_question

            if not st.session_state.answered:
                current_question = st.session_state.total_questions + 1
            else:
                current_question = st.session_state.total_questions

            st.write(
                f"**{t('question_progress').format(
                    current=current_question,
                    total=len(st.session_state.quiz_words)
                )}**"
            )

            # if st.session_state.quiz_type == "multiple_choice":
            #     st.write(f'### What does "{question["word"]}" mean?')

            #     answer = st.radio(
            #         "Choose an answer:",
            #         question["options"],
            #         index=None,
            #         key=f"quiz_answer_{st.session_state.answer_key_counter}"
            #     )
            if st.session_state.quiz_type == "multiple_choice":
                st.write(
                    f"### {t('what_does_mean').format(
                        word=question['word']
                    )}"
                )

                answer = st.radio(
                    t("choose_answer"),
                    question["options"],
                    index=None,
                    key=f"quiz_answer_{st.session_state.answer_key_counter}"
                )

            else:
                if st.session_state.gap_direction == "translation_to_word":
                    prompt_text = question["correct_answer"]

                else:
                    prompt_text = question["word"]

                st.write(
                    f"### {t('translate_prompt').format(
                        text=prompt_text
                    )}"
                )

                answer = st.text_input(
                    t("your_answer"),
                    key=f"quiz_answer_{st.session_state.answer_key_counter}"
                )

            if not st.session_state.answered:
                if st.button(t("check_answer")):


                    if answer is None or answer.strip() == "":
                        st.warning(t("enter_answer_first"))

                    else:
                        if st.session_state.quiz_type == "multiple_choice":
                            correct_answer_text = question["correct_answer"]

                            is_correct = (
                                answer == correct_answer_text
                            )

                        else:
                            if st.session_state.gap_direction == "translation_to_word":
                                correct_answer_text = question["word"]
                            else:
                                correct_answer_text = question["correct_answer"]

                            is_correct = (
                                answer.strip().lower()
                                == correct_answer_text.strip().lower()
                            )

                        st.session_state.total_questions += 1
                        st.session_state.answered = True
                        st.session_state.last_is_correct = is_correct
                        st.session_state.last_correct_answer = correct_answer_text

                        if is_correct:
                            st.session_state.score += 1
                            st.session_state.reaction = t(
                                random.choice(correct_reactions)
                            )

                        else:
                            st.session_state.reaction = t(
                            random.choice(wrong_reactions)
                        )

                            if question["word"] not in [
                                item["word"] for item in st.session_state.mistake_words
                            ]:
                                mistake_item = next(
                                    (
                                        item
                                        for item in st.session_state.vocabulary
                                        if item["word"] == question["word"]
                                    ),
                                    None
                                )

                                if mistake_item:
                                    st.session_state.mistake_words.append(mistake_item)

                        if (
                            st.session_state.total_questions
                            >= len(st.session_state.quiz_words)
                        ):
                            st.session_state.quiz_finished = True

                        st.rerun()

            else:
                is_correct = st.session_state.last_is_correct
                correct_answer_text = st.session_state.last_correct_answer

                if is_correct:
                    st.success(st.session_state.reaction)
                else:
                    st.error(
                        f"{st.session_state.reaction} "
                        f"{t('correct_answer_is').format(answer=correct_answer_text)}"
                    )

                if st.session_state.total_questions < len(st.session_state.quiz_words):
                    if st.button(t("next_question")):

                        st.session_state.next_debug = {
                            "retry": st.session_state.retry_mode,
                            "quiz_words": len(st.session_state.quiz_words),
                            "mistakes": len(st.session_state.mistake_words),
                            "total": st.session_state.total_questions,
                        }

                        correct_item = st.session_state.quiz_words[
                            st.session_state.total_questions
                        ]

                        st.session_state.quiz_question = create_question(correct_item)

                        st.session_state.answered = False
                        st.session_state.reaction = None
                        st.session_state.answer_key_counter += 1

                        st.rerun()
                        
                    if st.button(
                        t("end_quiz"),
                        key="end_regular_quiz"
                    ):
                        st.session_state.quiz_finished = True
                        st.rerun()

    if st.session_state.quiz_finished:
        st.subheader(t("quiz_complete"))

        st.write(
            f"### {t('final_score')}: "
            f"{st.session_state.score} / {st.session_state.total_questions}"
        )

        if st.session_state.total_questions > 0:
            percentage = (
                st.session_state.score
                / st.session_state.total_questions
                * 100
            )

            st.write(
                f"**{t('percent_correct').format(
                    percentage=f'{percentage:.0f}'
                )}**"
            )

            if st.session_state.quiz_type == "matching":
                st.write(
                    f"{t('questions_completed')}: "
                    f"{st.session_state.total_questions}"
                )
            else:
                st.write(
                    f"{t('questions_completed')}: "
                    f"{st.session_state.total_questions} / "
                    f"{len(st.session_state.quiz_words)}"
                )

        if st.session_state.mistake_words:
            if st.button(t("practice_mistakes")):
                st.session_state.retry_mode = True

                st.session_state.quiz_words = st.session_state.mistake_words.copy()
                st.session_state.quiz_length = len(st.session_state.quiz_words)

                st.session_state.mistake_words = []

                st.session_state.score = 0
                st.session_state.total_questions = 0
                st.session_state.answered = False
                st.session_state.quiz_finished = False
                st.session_state.reaction = None

                st.session_state.answer_key_counter += 1

                correct_item = st.session_state.quiz_words[0]
                st.session_state.quiz_question = create_question(correct_item)

                st.rerun()

        if st.button(t("start_new_quiz")):
            st.session_state.quiz_finished = False
            st.session_state.quiz_started = False
            st.session_state.quiz_question = None
            st.session_state.score = 0
            st.session_state.total_questions = 0
            st.session_state.answered = False
            st.session_state.reaction = None
            st.session_state.quiz_words = []

            if "quiz_answer" in st.session_state:
                del st.session_state.quiz_answer

            st.rerun()