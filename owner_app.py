import os
import runpy
import streamlit as st
from pathlib import Path

os.environ["QUIZFOX_APP_MODE"] = "owner"

CSS_FILE = Path(__file__).parent / "style.css"

with open(CSS_FILE) as css_file:
    st.markdown(
        f"<style>{css_file.read()}</style>",
        unsafe_allow_html=True
    )

OWNER_TEXTS = {
    "en": {
        "title": "🦊 QuizFox Teacher",
        "login_prompt": "Please log in to continue.",
        "login_button": "Log in with Google",
        "access_denied": "Access denied.",
        "signed_in_as": "Signed in as",
        "logout": "Log out",
    },
    "ru": {
        "title": "🦊 QuizFox Teacher",
        "login_prompt": "Войдите, чтобы продолжить.",
        "login_button": "Войти через Google",
        "access_denied": "Доступ запрещён.",
        "signed_in_as": "Вы вошли как",
        "logout": "Выйти",
    },
}

text = OWNER_TEXTS["en"]

ALLOWED_EMAILS = {
    "iana.korshunova.work@gmail.com",
    "lanawang172@gmail.com",
}


if not st.user.is_logged_in:
    left, center, right = st.columns([1, 2, 1])

    with center:
        st.markdown(
            '<div class="teacher-login-title">🦊 QuizFox Teacher</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="teacher-login-text">'
            'Please log in to continue.'
            '</div>',
            unsafe_allow_html=True
        )

        if st.button(
            "Log in with Google",
            use_container_width=True
        ):
            st.login()

    st.stop()

if st.user.email not in ALLOWED_EMAILS:
    st.error("Access denied.")

    if st.button("Log out"):
        st.logout()

    st.stop()

st.sidebar.write(
    f"Signed in as: {st.user.email}"
)

if st.sidebar.button("Log out"):
    st.logout()


runpy.run_path("app.py")