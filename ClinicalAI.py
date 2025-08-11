import streamlit as st
import sqlite3
import uuid
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "app_data.db"

# Database Setup & Connection
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    return conn

conn = init_db()

# Utilities
def now_iso():
    return datetime.utcnow().isoformat()

# Authentication
def create_user(email, password):
    c = conn.cursor()
    uid = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    try:
        c.execute("INSERT INTO users (id,email,password_hash,created_at) VALUES (?,?,?,?)",
                  (uid, email, pw_hash, now_iso()))
        conn.commit()
        return uid
    except Exception:
        return None

def authenticate(email, password):
    c = conn.cursor()
    c.execute("SELECT id,password_hash FROM users WHERE email=?", (email,))
    r = c.fetchone()
    if r and check_password_hash(r[1], password):
        return r[0]
    return None

# UI Pages
def show_login():
    st.title("Clinical AI Assistant Login or Signup")
    option = st.selectbox("Choose an option", ["Sign In", "Sign Up", "Continue as Guest"])
    if option == "Sign Up":
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            uid = create_user(email, password)
            if uid:
                st.success("Account created! Please sign in.")
            else:
                st.error("Email already exists or invalid.")
    elif option == "Sign In":
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        if st.button("Sign In"):
            uid = authenticate(email, password)
            if uid:
                st.session_state.user_id = uid
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")
    else:
        if st.button("Continue as Guest"):
            st.session_state.user_id = "guest"
            st.experimental_rerun()

def show_logout():
    st.sidebar.write(f"Logged in as: {st.session_state.user_id}")
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.experimental_rerun()

def chatgpt_research():
    st.header("ChatGPT Research")
    st.markdown("Click the button below to open ChatGPT in a new tab.")
    if st.button("Open ChatGPT"):
        js = "window.open('https://chat.openai.com/chat', '_blank')"
        st.components.v1.html(f"<script>{js}</script>", height=0, width=0)

def main_menu():
    options = ["ChatGPT Research"]
    choice = st.sidebar.selectbox("Menu", options)
    return choice

def main():
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        show_login()
    else:
        show_logout()
        choice = main_menu()
        if choice == "ChatGPT Research":
            chatgpt_research()

if __name__ == "__main__":
    main()
