import streamlit as st
import random
import re
from pathlib import Path
import base64
import json
import psycopg
import os

database_url = st.secrets["NEON_DATABASE_URL"]

APP_MODE = os.getenv(
    "QUIZFOX_APP_MODE",
    st.secrets.get("APP_MODE", "demo")
)

DEMO_MODE = APP_MODE == "demo"

if DEMO_MODE:
    st.info(
        "Portfolio demo — database changes are disabled. "
        "You can add vocabulary and try quizzes, but changes won’t be saved."
    )

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
    "🦊 Correct!",
    "🦊 Fox-approved!",
    "🦊 Nice one!",
    "🦊 Nailed it!",
    "🦊 The fox is impressed."
]

wrong_reactions = [
    "🦊 Almost!",
    "🦊 Sneaky question!",
    "🦊 Not this time!",
    "🦊 The fox demands another attempt.",
    "🦊 So close!"
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

st.session_state.vocabulary_sets = load_sets_from_db()

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

page = st.sidebar.radio(
    "Navigation",
    ["Vocabulary", "Quiz"]
)

# -------------------------
# Add vocabulary
# -------------------------

if page == "Vocabulary":

    st.subheader("Add vocabulary")

    st.subheader("Import vocabulary")

    if st.session_state.clear_bulk_vocabulary:
        st.session_state.bulk_vocabulary_input = ""
        st.session_state.clear_bulk_vocabulary = False

    if st.session_state.import_message:
        st.success(st.session_state.import_message)
        st.session_state.import_message = None

    bulk_vocabulary = st.text_area(
        "Paste vocabulary (one pair per line; use a tab, —, or 2+ spaces):",
        placeholder="forest\tлес\nocean\tокеан\ncity\tгород",
        key="bulk_vocabulary_input"
    )

    if st.button("Import vocabulary"):
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

                st.session_state.import_message = (
                    f"Imported {len(new_words)} new words."
                )

                st.session_state.clear_bulk_vocabulary = True
                st.rerun()

            else:
                st.info(
                    "All these words are already in the vocabulary set."
                )

        else:
            st.warning(
                "No valid vocabulary pairs found."
            )

    if st.session_state.clear_add_form:
        st.session_state.word_input = ""
        st.session_state.translation_input = ""
        st.session_state.clear_add_form = False

    word = st.text_input("Word", key="word_input")
    translation = st.text_input("Translation", key="translation_input")

    if st.button("Add word"):
        if word and translation:
            st.session_state.vocabulary.append(
                {
                    "word": word,
                    "translation": translation
                }
            )

            st.session_state.clear_add_form = True
            st.session_state.added_message = f"Added: {word} — {translation}"
            st.rerun()

        else:
            st.warning("Please enter both the word and the translation.")

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
        st.subheader("Vocabulary set")

        if st.button("Clear vocabulary"):
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
            col1, col2, col3 = st.columns([5, 1, 1])

            with col1:
                st.markdown(
                    f"**{item['word']}** — {item['translation']}"
                )

            with col2:
                if st.button(
                    "Edit",
                    key=f"edit_word_{index}"
                ):
                    st.session_state.editing_word_index = index
                    st.rerun()

            with col3:
                if st.button(
                    "Delete",
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
                    "Word",
                    value=item["word"],
                    key=f"edited_word_{index}"
                )

                edited_translation = st.text_input(
                    "Translation",
                    value=item["translation"],
                    key=f"edited_translation_{index}"
                )

                save_col, cancel_col = st.columns(2)

                with save_col:
                    if st.button(
                        "Save changes",
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
                                    "This vocabulary pair already exists."
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
                                "Word and translation cannot be empty."
                            )

                with cancel_col:
                    if st.button(
                        "Cancel",
                        key=f"cancel_edit_{index}"
                    ):
                        st.session_state.editing_word_index = None
                        st.rerun()

    st.subheader("Saved sets")

    if st.session_state.save_set_message:
        st.success(st.session_state.save_set_message)
        st.session_state.save_set_message = None

    if st.session_state.clear_set_name:
        st.session_state.set_name_input = ""
        st.session_state.clear_set_name = False

    set_name = st.text_input(
        "Set name",
        placeholder="e.g. Nature A2",
        key="set_name_input"
    )

    if st.button(
        "Save set",
        disabled=DEMO_MODE
    ):
        clean_set_name = set_name.strip()

        if not clean_set_name:
            st.warning("Enter a set name first.")

        elif not st.session_state.vocabulary:
            st.warning("Add some vocabulary first.")

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
                f'Set "{clean_set_name}" saved!'
            )

            st.rerun()

    if st.session_state.confirm_replace_set:
        replace_set_name = st.session_state.replace_set_name

        st.warning(
            f'Set "{replace_set_name}" already exists. Replace it?'
        )

        replace_col, cancel_replace_col = st.columns(2)

        with replace_col:
            if st.button(
                "Yes, replace",
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
            if st.button("Cancel replace"):
                st.session_state.confirm_replace_set = False
                st.session_state.replace_set_name = None
                st.rerun()

    if st.session_state.vocabulary_sets:
        st.write("### Your saved sets")

        selected_set = st.selectbox(
            "Choose a set",
            list(st.session_state.vocabulary_sets.keys()),
            format_func=lambda name: (
                f"{name} — "
                f"{len(st.session_state.vocabulary_sets[name])} words"
            )
        )

        if st.button("Load set"):
            st.session_state.vocabulary = [
                item.copy()
                for item in st.session_state.vocabulary_sets[selected_set]
            ]

            st.session_state.load_message = (
                f'Set "{selected_set}" loaded!'
            )

            st.rerun()

        if not st.session_state.confirm_delete_set:
            if st.button(
                "Delete set",
                disabled=DEMO_MODE
            ):
                st.session_state.confirm_delete_set = True
                st.session_state.delete_set_name = selected_set
                st.rerun()

        else:
            delete_set_name = st.session_state.delete_set_name

            st.warning(
                f'Delete set "{delete_set_name}"?'
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                if st.button(
                    "Yes, delete",
                    disabled=DEMO_MODE
                ):
                    delete_set_from_db(delete_set_name)

                    st.session_state.vocabulary_sets = load_sets_from_db()

                    st.session_state.confirm_delete_set = False
                    st.session_state.delete_set_name = None
                    st.rerun()

            with cancel_col:
                if st.button("Cancel"):
                    st.session_state.confirm_delete_set = False
                    st.session_state.delete_set_name = None
                    st.rerun()

        if not st.session_state.renaming_set:
            if st.button(
                "Rename set",
                disabled=DEMO_MODE
            ):
                st.session_state.renaming_set = True
                st.session_state.rename_set_name = selected_set
                st.rerun()

        if st.session_state.renaming_set:
            old_name = st.session_state.rename_set_name

            new_name = st.text_input(
                "New set name",
                value=old_name
            )

            rename_col, cancel_rename_col = st.columns(2)

            with rename_col:
                if st.button(
                    "Save new name",
                    disabled=DEMO_MODE
                ):
                    new_name = new_name.strip()

                    if not new_name:
                        st.warning("Set name cannot be empty.")

                    elif (
                        new_name != old_name
                        and new_name in st.session_state.vocabulary_sets
                    ):
                        st.warning("A set with this name already exists.")

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
                if st.button("Cancel rename"):
                    st.session_state.renaming_set = False
                    st.session_state.rename_set_name = None
                    st.rerun()

# -------------------------
# Quiz
# -------------------------

elif page == "Quiz":
    st.divider()
    st.subheader("Quiz")

    st.write(
        f"🦊 **Score: {st.session_state.score} / "
        f"{st.session_state.total_questions}**"
    )

    if len(st.session_state.vocabulary) < 4:
        st.info("Add at least 4 words to generate a quiz.")

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
                "Number of questions:",
                quiz_options,
                horizontal=True
            )

            quiz_type = st.radio(
                "Quiz type:",
                ["Multiple Choice", "Gap Fill", "Matching"],
                horizontal=True
            )

            if quiz_type == "Gap Fill":
                gap_direction = st.radio(
                    "Gap Fill direction:",
                    [
                        "Translation → Word",
                        "Word → Translation"
                    ],
                    horizontal=True
                )

            if st.button("Start quiz"):
                st.session_state.mistake_words = []
                st.session_state.retry_mode = False
                st.session_state.quiz_type = quiz_type
                st.session_state.score = 0
                st.session_state.total_questions = 0
                st.session_state.reaction = None
                st.session_state.quiz_finished = False
                st.session_state.quiz_length = quiz_length
                st.session_state.answer_key_counter += 1

                if quiz_type == "Matching":
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
        
        if st.session_state.quiz_type == "Matching":
            st.subheader("Match the words")

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
                if st.button("Check matches"):
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
                            f"{item['word']} — correct: {item['translation']}"
                        )

                st.write(
                    f"### Matching score: "
                    f"{matching_score} / {len(st.session_state.matching_pairs)}"
                )

                if matching_score == len(st.session_state.matching_pairs):
                    st.success("🦊 Perfect match!")
                elif matching_score >= len(st.session_state.matching_pairs) / 2:
                    st.info("🦊 Nice work!")
                else:
                    st.error("🦊 Keep going!")

                if st.button("Next matching round"):
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

                if st.button("End quiz", key="end_matching_quiz"):
                    st.session_state.quiz_finished = True
                    st.rerun()

        else:
            question = st.session_state.quiz_question

            if not st.session_state.answered:
                current_question = st.session_state.total_questions + 1
            else:
                current_question = st.session_state.total_questions

            st.write(
                f"**Question {current_question} "
                f"of {len(st.session_state.quiz_words)}**"
            )

            if st.session_state.quiz_type == "Multiple Choice":
                st.write(f'### What does "{question["word"]}" mean?')

                answer = st.radio(
                    "Choose an answer:",
                    question["options"],
                    index=None,
                    key=f"quiz_answer_{st.session_state.answer_key_counter}"
                )

            else:
                if st.session_state.gap_direction == "Translation → Word":
                    prompt_text = question["correct_answer"]

                else:
                    prompt_text = question["word"]

                st.write(
                    f'### Translate **"{prompt_text}"**'
                )

                answer = st.text_input(
                    "Your answer:",
                    key=f"quiz_answer_{st.session_state.answer_key_counter}"
                )

            if not st.session_state.answered:
                if st.button("Check answer"):

                    if answer is None or answer.strip() == "":
                        st.warning("Enter an answer first.")

                    else:
                        if st.session_state.quiz_type == "Multiple Choice":
                            correct_answer_text = question["correct_answer"]

                            is_correct = (
                                answer == correct_answer_text
                            )

                        else:
                            if st.session_state.gap_direction == "Translation → Word":
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
                            st.session_state.reaction = random.choice(
                                correct_reactions
                            )

                        else:
                            st.session_state.reaction = random.choice(
                                wrong_reactions
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
                        f"The correct answer is: {correct_answer_text}"
                    )

                if st.session_state.total_questions < len(st.session_state.quiz_words):
                    if st.button("Next question"):

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
                        
                    if st.button("End quiz", key="end_regular_quiz"):
                        st.session_state.quiz_finished = True
                        st.rerun()

    if st.session_state.quiz_finished:
        st.subheader("Quiz complete! 🦊")

        st.write(
            f"### Final score: "
            f"{st.session_state.score} / {st.session_state.total_questions}"
        )

        if st.session_state.total_questions > 0:
            percentage = (
                st.session_state.score
                / st.session_state.total_questions
                * 100
            )

            st.write(f"**{percentage:.0f}% correct**")

            if st.session_state.quiz_type == "Matching":
                st.write(
                    f"Questions completed: "
                    f"{st.session_state.total_questions}"
                )
            else:
                st.write(
                    f"Questions completed: "
                    f"{st.session_state.total_questions} / "
                    f"{len(st.session_state.quiz_words)}"
                )

        if st.session_state.mistake_words:
            if st.button("Practice mistakes"):
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

        if st.button("Start new quiz"):
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