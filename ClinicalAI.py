# app.py
# Clinical AI Assistant - single-file Streamlit app
# Features: menu/navigation, ChatGPT external button, quizzes, flashcards,
# daily check-ins, motivational quotes, study charts, planner/reminders, mnemonics,
# bank vault notes, basic signup/signin, optional vault encryption (session-only password)

import streamlit as st
from streamlit.components.v1 import components
import sqlite3
import os
import json
import uuid
import base64
import requests
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import matplotlib.pyplot as plt

# optional encryption libs
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# -----------------------
# Configuration
# -----------------------
DB_PATH = "app_data.db"
SUBJECTS = [
    "Pharmacology","Microbiology","Hematology","Pathology","Forensic Medicine",
    "Obstetrics and Gynecology","Pediatrics","Community and Public Medicine"
]

# -----------------------
# Database initialization
# -----------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, created_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS quizzes (
        id TEXT PRIMARY KEY, user_id TEXT, title TEXT, data TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY, user_id TEXT, front TEXT, back TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS checkins (
        id TEXT PRIMARY KEY, user_id TEXT, date TEXT, mood TEXT, focus INTEGER,
        hours REAL, notes TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS quotes (
        id TEXT PRIMARY KEY, user_id TEXT, quote TEXT, author TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id TEXT PRIMARY KEY, user_id TEXT, title TEXT, remind_at TEXT, notes TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS mnemonics (
        id TEXT PRIMARY KEY, user_id TEXT, course TEXT, topic TEXT, name TEXT, content TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS vault_notes (
        id TEXT PRIMARY KEY, user_id TEXT, subject TEXT, title TEXT, content TEXT, encrypted INTEGER DEFAULT 0, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    conn.commit()
    return conn

conn = init_db()

# -----------------------
# Utility functions
# -----------------------
def now_iso():
    return datetime.utcnow().isoformat()

def create_user(email, password):
    c = conn.cursor()
    uid = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    try:
        c.execute("INSERT INTO users (id,email,password_hash,created_at) VALUES (?,?,?,?)",
                  (uid, email, pw_hash, now_iso()))
        conn.commit()
        return uid
    except sqlite3.IntegrityError:
        return None

def authenticate(email, password):
    c = conn.cursor()
    c.execute("SELECT id,password_hash FROM users WHERE email=?", (email,))
    r = c.fetchone()
    if not r:
        return None
    uid, pw_hash = r
    if check_password_hash(pw_hash, password):
        return uid
    return None

# -----------------------
# CRUD helpers (quizzes, flashcards, checkins, quotes, reminders, mnemonics, vault)
# -----------------------
def insert_quiz(user_id, title, data_json):
    c = conn.cursor()
    qid = str(uuid.uuid4())
    c.execute("INSERT INTO quizzes (id,user_id,title,data,created_at) VALUES (?,?,?,?,?)",
              (qid, user_id, title, json.dumps(data_json), now_iso()))
    conn.commit()

def list_quizzes(user_id):
    c = conn.cursor()
    c.execute("SELECT id,title,data FROM quizzes WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    return [{'id': r[0], 'title': r[1], 'data': json.loads(r[2])} for r in rows]

def delete_quiz(qid, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM quizzes WHERE id=? AND user_id=?", (qid, user_id))
    conn.commit()

def add_flashcard(user_id, front, back):
    c = conn.cursor()
    fid = str(uuid.uuid4())
    c.execute("INSERT INTO flashcards (id,user_id,front,back,created_at) VALUES (?,?,?,?,?)",
              (fid, user_id, front, back, now_iso()))
    conn.commit()

def list_flashcards(user_id):
    c = conn.cursor()
    c.execute("SELECT id,front,back FROM flashcards WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'front': r[1], 'back': r[2]} for r in c.fetchall()]

def add_checkin(user_id, date, mood, focus, hours, notes):
    c = conn.cursor()
    cid = str(uuid.uuid4())
    c.execute("INSERT INTO checkins (id,user_id,date,mood,focus,hours,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
              (cid, user_id, date, mood, focus, hours, notes, now_iso()))
    conn.commit()

def list_checkins(user_id):
    c = conn.cursor()
    c.execute("SELECT id,date,mood,focus,hours,notes FROM checkins WHERE user_id=? ORDER BY date ASC", (user_id,))
    rows = c.fetchall()
    return [{'id': r[0], 'date': r[1], 'mood': r[2], 'focus': r[3], 'hours': r[4], 'notes': r[5]} for r in rows]

def add_quote(user_id, quote, author=''):
    c = conn.cursor()
    qid = str(uuid.uuid4())
    c.execute("INSERT INTO quotes (id,user_id,quote,author,created_at) VALUES (?,?,?,?,?)",
              (qid, user_id, quote, author, now_iso()))
    conn.commit()

def list_quotes(user_id):
    c = conn.cursor()
    c.execute("SELECT id,quote,author FROM quotes WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'quote': r[1], 'author': r[2]} for r in c.fetchall()]

def add_reminder(user_id, title, remind_at, notes=''):
    c = conn.cursor()
    rid = str(uuid.uuid4())
    c.execute("INSERT INTO reminders (id,user_id,title,remind_at,notes,created_at) VALUES (?,?,?,?,?,?)",
              (rid, user_id, title, remind_at, notes, now_iso()))
    conn.commit()

def list_reminders(user_id):
    c = conn.cursor()
    c.execute("SELECT id,title,remind_at,notes FROM reminders WHERE user_id=? ORDER BY remind_at ASC", (user_id,))
    return [{'id': r[0], 'title': r[1], 'remind_at': r[2], 'notes': r[3]} for r in c.fetchall()]

def add_mnemonic(user_id, course, topic, name, content):
    c = conn.cursor()
    mid = str(uuid.uuid4())
    c.execute("INSERT INTO mnemonics (id,user_id,course,topic,name,content,created_at) VALUES (?,?,?,?,?,?,?)",
              (mid, user_id, course, topic, name, content, now_iso()))
    conn.commit()

def list_mnemonics(user_id):
    c = conn.cursor()
    c.execute("SELECT id,course,topic,name,content FROM mnemonics WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'course': r[1], 'topic': r[2], 'name': r[3], 'content': r[4]} for r in c.fetchall()]

def add_vault_note(user_id, subject, title, content, encrypted=0):
    if subject not in SUBJECTS:
        raise ValueError('Unknown subject')
    c = conn.cursor()
    vid = str(uuid.uuid4())
    c.execute("INSERT INTO vault_notes (id,user_id,subject,title,content,encrypted,created_at) VALUES (?,?,?,?,?,?,?)",
              (vid, user_id, subject, title, content, encrypted, now_iso()))
    conn.commit()

def list_vault_notes(user_id, subject=None):
    c = conn.cursor()
    if subject:
        c.execute("SELECT id,subject,title,content,encrypted FROM vault_notes WHERE user_id=? AND subject=?", (user_id, subject))
    else:
        c.execute("SELECT id,subject,title,content,encrypted FROM vault_notes WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'subject': r[1], 'title': r[2], 'content': r[3], 'encrypted': r[4]} for r in c.fetchall()]

# -----------------------
# Login/signup UI integrated as requested
# -----------------------
def show_login():
    st.title("Clinical AI Assistant Login or Signup")
    option = st.selectbox("Choose an option", ["Sign In", "Sign Up", "Continue as Guest"])
    
    if option == "Sign Up":
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            if not email or not password:
                st.error("Email and password are required")
                return
            uid = create_user(email, password)
            if uid:
                st.success("Account created! Please sign in.")
            else:
                st.error("Email already exists or invalid.")
    
    elif option == "Sign In":
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        if st.button("Sign In"):
            if not email or not password:
                st.error("Please enter both email and password")
                return
            uid = authenticate(email, password)
            if uid:
                st.session_state.user_id = uid
                st.success("Signed in successfully")
                st.experimental_rerun()
                return
            else:
                st.error("Invalid credentials.")
    
    else:  # Guest
        if st.button("Continue as Guest"):
            st.session_state.user_id = "guest"
            st.experimental_rerun()
            return

# -----------------------
# Main app
# -----------------------
def main():
    st.set_page_config(page_title="Clinical AI Assistant", layout="wide")

    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.user_id:
        show_login()
        return

    user_id = st.session_state.user_id

    # Navigation menu
    menu = [
        "Home","ChatGPT (external)","Quizzes","Flashcards",
        "Daily Check-in","Quotes","Study Planner","Study Charts",
        "Mnemonics","Bank Vaults","Settings"
    ]
    page = st.sidebar.radio("Navigate", menu)

    # Top bar with sign out
    st.sidebar.markdown(f"**Signed in as:** {user_id}")
    if st.sidebar.button("Sign out"):
        st.session_state.user_id = None
        st.experimental_rerun()

    # Pages
    if page == "Home":
        st.header("Clinical AI Assistant")
        st.write("Welcome to your Clinical AI Assistant. Use the sidebar to navigate through features.")

    elif page == "ChatGPT (external)":
        st.header("External ChatGPT")
        st.write("This opens chat.openai.com in a new tab where you can use ChatGPT directly.")
        if st.button("Open ChatGPT (External)"):
            st.markdown("[Go to ChatGPT](https://chat.openai.com)", unsafe_allow_html=True)

    elif page == "Quizzes":
        st.header("Quizzes")
        quizzes = list_quizzes(user_id)
        for q in quizzes:
            st.subheader(q['title'])
            for i, item in enumerate(q['data']):
                st.write(f"Q{i+1}: {item['question']}")
                for o in item.get('options', []):
                    st.write(f"- {o}")
                st.write(f"Answer: {item['answer']}")
            if st.button(f"Delete Quiz: {q['title']}", key=f"del_{q['id']}"):
                delete_quiz(q['id'], user_id)
                st.experimental_rerun()
        st.markdown("### Add New Quiz")
        title = st.text_input("Quiz title")
        qjson = st.text_area(
            "Quiz JSON (list of {question, options, answer} objects)",
            height=200
        )
        if st.button("Add Quiz"):
            try:
                data_json = json.loads(qjson)
                insert_quiz(user_id, title, data_json)
                st.success("Quiz added.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Invalid JSON or error: {e}")

    elif page == "Flashcards":
        st.header("Flashcards")
        flashcards = list_flashcards(user_id)
        for f in flashcards:
            st.write(f"**{f['front']}** — {f['back']}")
        st.markdown("### Add Flashcard")
        front = st.text_input("Front")
        back = st.text_input("Back")
        if st.button("Add Flashcard"):
            add_flashcard(user_id, front, back)
            st.success("Flashcard added.")
            st.experimental_rerun()

    elif page == "Daily Check-in":
        st.header("Daily Check-in")
        today_str = datetime.today().strftime("%
