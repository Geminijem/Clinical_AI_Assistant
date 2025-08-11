import streamlit as st
import sqlite3
import uuid
import json
import base64
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import pandas as pd
import matplotlib.pyplot as plt

# --- Configuration ---
DB_PATH = "app_data.db"
SUBJECTS = [
    "Pharmacology","Microbiology","Hematology","Pathology","Forensic Medicine",
    "Obstetrics and Gynecology","Pediatrics","Community and Public Medicine"
]

# --- Database Setup ---
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Users
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    # Quizzes
    c.execute("""CREATE TABLE IF NOT EXISTS quizzes (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        data TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Flashcards
    c.execute("""CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        front TEXT,
        back TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Check-ins
    c.execute("""CREATE TABLE IF NOT EXISTS checkins (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        date TEXT,
        mood TEXT,
        focus INTEGER,
        hours REAL,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Quotes
    c.execute("""CREATE TABLE IF NOT EXISTS quotes (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        quote TEXT,
        author TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Reminders / Planner
    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        remind_at TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Mnemonics
    c.execute("""CREATE TABLE IF NOT EXISTS mnemonics (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        course TEXT,
        topic TEXT,
        name TEXT,
        content TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    # Vault notes
    c.execute("""CREATE TABLE IF NOT EXISTS vault_notes (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        subject TEXT,
        title TEXT,
        content TEXT,
        encrypted INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- Utilities ---
def now_iso():
    return datetime.utcnow().isoformat()

# --- Auth ---
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
        return {"id": uid}
    return None

# --- CRUD helpers ---
def insert_quiz(user_id, title, data_json):
    c = conn.cursor()
    qid = str(uuid.uuid4())
    c.execute("INSERT INTO quizzes (id,user_id,title,data,created_at) VALUES (?,?,?,?,?)",
              (qid, user_id, title, json.dumps(data_json), now_iso()))
    conn.commit()

def list_quizzes(user_id):
    c = conn.cursor()
    c.execute("SELECT id,title,data,created_at FROM quizzes WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    return [{'id': r[0], 'title': r[1], 'data': json.loads(r[2]), 'created_at': r[3]} for r in rows]

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
    c.execute("SELECT id,front,back,created_at FROM flashcards WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'front': r[1], 'back': r[2], 'created_at': r[3]} for r in c.fetchall()]

def add_checkin(user_id, date, mood, focus, hours, notes):
    c = conn.cursor()
    cid = str(uuid.uuid4())
    c.execute("INSERT INTO checkins (id,user_id,date,mood,focus,hours,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
              (cid, user_id, date, mood, focus, hours, notes, now_iso()))
    conn.commit()

def list_checkins(user_id):
    c = conn.cursor()
    c.execute("SELECT id,date,mood,focus,hours,notes,created_at FROM checkins WHERE user_id=? ORDER BY date ASC", (user_id,))
    rows = c.fetchall()
    return [{'id': r[0], 'date': r[1], 'mood': r[2], 'focus': r[3], 'hours': r[4], 'notes': r[5], 'created_at': r[6]} for r in rows]

def add_quote(user_id, quote, author=''):
    c = conn.cursor()
    qid = str(uuid.uuid4())
    c.execute("INSERT INTO quotes (id,user_id,quote,author,created_at) VALUES (?,?,?,?,?)",
              (qid, user_id, quote, author, now_iso()))
    conn.commit()

def list_quotes(user_id):
    c = conn.cursor()
    c.execute("SELECT id,quote,author,created_at FROM quotes WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'quote': r[1], 'author': r[2], 'created_at': r[3]} for r in c.fetchall()]

def add_reminder(user_id, title, remind_at, notes=''):
    c = conn.cursor()
    rid = str(uuid.uuid4())
    c.execute("INSERT INTO reminders (id,user_id,title,remind_at,notes,created_at) VALUES (?,?,?,?,?,?)",
              (rid, user_id, title, remind_at, notes, now_iso()))
    conn.commit()

def list_reminders(user_id):
    c = conn.cursor()
    c.execute("SELECT id,title,remind_at,notes,created_at FROM reminders WHERE user_id=? ORDER BY remind_at ASC", (user_id,))
    return [{'id': r[0], 'title': r[1], 'remind_at': r[2], 'notes': r[3], 'created_at': r[4]} for r in c.fetchall()]

def add_mnemonic(user_id, course, topic, name, content):
    c = conn.cursor()
    mid = str(uuid.uuid4())
    c.execute("INSERT INTO mnemonics (id,user_id,course,topic,name,content,created_at) VALUES (?,?,?,?,?,?,?)",
              (mid, user_id, course, topic, name, content, now_iso()))
    conn.commit()

def list_mnemonics(user_id):
    c = conn.cursor()
    c.execute("SELECT id,course,topic,name,content,created_at FROM mnemonics WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'course': r[1], 'topic': r[2], 'name': r[3], 'content': r[4], 'created_at': r[5]} for r in c.fetchall()]

def add_vault_note(user_id, subject, title, content):
    if subject not in SUBJECTS:
        raise ValueError('Unknown subject')
    c = conn.cursor()
    vid = str(uuid.uuid4())
    c.execute("INSERT INTO vault_notes (id,user_id,subject,title,content,created_at) VALUES (?,?,?,?,?,?)",
              (vid, user_id, subject, title, content, now_iso()))
    conn.commit()

def list_vault_notes(user_id, subject=None):
    c = conn.cursor()
    if subject:
        c.execute("SELECT id,subject,title,content,created_at FROM vault_notes WHERE user_id=? AND subject=?", (user_id, subject))
    else:
        c.execute("SELECT id,subject,title,content,created_at FROM vault_notes WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'subject': r[1], 'title': r[2], 'content': r[3], 'created_at': r[4]} for r in c.fetchall()]

# --- Streamlit UI ---
st.set_page_config(page_title="Clinical AI Assistant", layout="wide")

if 'user' not in st.session_state:
    st.session_state.user = None

def show_login():
    st.title("Clinical AI Assistant - Login or Signup")
    mode = st.radio("Choose action:", ["Sign In", "Sign Up", "Continue as Guest"])
    if mode == "Sign Up":
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            uid = create_user(email, password)
            if uid:
                st.success("Account created! Please sign in.")
            else:
                st.error("Email already exists.")
    elif mode == "Sign In":
        email = st.text_input("Email", key="signin_email")
        password = st.text_input("Password", type="password", key="signin_password")
        if st.button("Sign In"):
            auth = authenticate(email, password)
            if auth:
                st.session_state.user = auth
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")
    else:
        if st.button("Continue as Guest"):
            st.session_state.user = {"id": "guest"}
            st.experimental_rerun()

def show_logout():
    st.sidebar.write("Logged in as user")
    if st.sidebar.button("Sign Out"):
        st.session_state.user = None
        st.experimental_rerun()

def main_menu():
    menu = ["ChatGPT Research", "Quizzes", "Flashcards", "Daily Check-in", "Motivational Quotes", "Study Planner", "Mnemonics", "Bank Vault"]
    choice = st.sidebar.selectbox("Select Feature", menu)
    return choice

def chatgpt_research():
    st.header("ChatGPT Research")
    st.markdown("""
    You can click the button below to open ChatGPT in a new tab to do your medical research and questions.
    """)
    if st.button("Open ChatGPT", key="open_chatgpt"):
        js = "window.open('https://chat.openai.com/chat', '_blank')"
        st.components.v1.html(f"<script>{js}</script>")

def quizzes_page(user_id):
    st.header("Your Quizzes")
    quizzes = list_quizzes(user_id)
    for q in quizzes:
        with st.expander(q['title']):
            st.json(q['data'])
            if st.button(f"Delete Quiz: {q['title']}", key=f"delquiz_{q['id']}"):
                delete_quiz(q['id'], user_id)
                st.experimental_rerun()
    st.subheader("Add New Quiz")
    title = st.text_input("Quiz Title")
    data = st.text_area("Quiz Data JSON")
    if st.button("Add Quiz"):
        try:
            data_json = json.loads(data)
            insert_quiz(user_id, title, data_json)
            st.success("Quiz added")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Invalid JSON data: {e}")

def flashcards_page(user_id):
    st.header("Your Flashcards")
    flashcards = list_flashcards(user_id)
    for f in flashcards:
        with st.expander(f['front']):
            st.write(f"Answer: {f['back']}")
    st.subheader("Add New Flashcard")
    front = st.text_input("Front")
    back = st.text_input("Back")
    if st.button("Add Flashcard"):
        if front and back:
            add_flashcard(user_id, front, back)
            st.success("Flashcard added")
            st.experimental_rerun()
        else:
            st.error("Both front and back required")

def checkin_page(user_id):
    st.header("Daily Check-in")
    today = datetime.utcnow().date().isoformat()
    mood = st.selectbox("Mood", ["Happy", "Neutral", "Sad", "Stressed"])
    focus = st.slider("Focus level (1-10)", 1, 10, 5)
    hours = st.number_input("Hours studied today", min_value=0.0, max_value=24.0, step=0.25)
    notes = st.text_area("Notes")
    if st.button("Submit Check-in"):
        add_checkin(user_id, today, mood, focus, hours, notes)
        st.success("Check-in saved")
        st.experimental_rerun()
    st.subheader("Past Check-ins")
    checkins = list_checkins(user_id)
    if checkins:
        df = pd.DataFrame(checkins)
        st.dataframe(df[['date','mood','focus','hours','notes']])
        fig, ax = plt.subplots()
        ax.plot(df['date'], df['focus'], marker='o')
        ax.set_title("Focus Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Focus")
        plt.xticks(rotation=45)
        st.pyplot(fig)

def quotes_page(user_id):
    st.header("Motivational Quotes")
    quotes = list_quotes(user_id)
    if quotes:
        q = st.selectbox("Choose a quote", quotes, format_func=lambda x: f"{x['quote']} - {x['author']}")
        if q:
            st.markdown(f"> {q['quote']}\n\n— *{q['author']}*")
    st.subheader("Add New Quote")
    quote = st.text_input("Quote")
    author = st.text_input("Author")
    if st.button("Add Quote"):
        if quote:
            add_quote(user_id, quote, author)
            st.success("Quote added")
            st.experimental_rerun()
        else:
            st.error("Quote cannot be empty")

def planner_page(user_id):
    st.header("Study Planner & Reminders")
    reminders = list_reminders(user_id)
    st.subheader("Your Reminders")
    for r in reminders:
        st.write(f"- {r['title']} at {r['remind_at']} — {r['notes']}")
    st.subheader("Add Reminder")
    title = st.text_input("Title")
    remind_at = st.text_input("Remind at (YYYY-MM-DD HH:MM)")
    notes = st.text_area("Notes")
    if st.button("Add Reminder"):
        try:
            datetime.strptime(remind_at, "%Y-%m-%d %H:%M")
            add_reminder(user_id, title, remind_at, notes)
            st.success("Reminder added")
            st.experimental_rerun()
        except:
            st.error("Invalid datetime format")

def mnemonics_page(user_id):
    st.header("Mnemonics")
    mnemonics = list_mnemonics(user_id)
    for m in mnemonics:
        with st.expander(f"{m['course']} - {m['topic']} - {m['name']}"):
            st.write(m['content'])
    st.subheader("Add New Mnemonic")
    course = st.selectbox("Course", SUBJECTS)
    topic = st.text_input("Topic")
    name = st.text_input("Mnemonic Name")
    content = st.text_area("Content")
    if st.button("Add Mnemonic"):
        if course and topic and name and content:
            add_mnemonic(user_id, course, topic, name, content)
            st.success("Mnemonic added")
            st.experimental_rerun()
        else:
            st.error("All fields required")

def vault_page(user_id):
    st.header("Bank Vault Notes")
    subject = st.selectbox("Subject", ["All"] + SUBJECTS)
    selected_subject = None if subject == "All" else subject
    notes = list_vault_notes(user_id, selected_subject)
    for note in notes:
        with st.expander(f"{note['subject']} - {note['title']}"):
            st.write(note['content'])
    st.subheader("Add New Vault Note")
    sub = st.selectbox("Subject for new note", SUBJECTS, key="new_note_subject")
    title = st.text_input("Title", key="new_note_title")
    content = st.text_area("Content", key="new_note_content")
    if st.button("Add Vault Note"):
        if sub and title and content:
            add_vault_note(user_id, sub, title, content)
            st.success("Vault note added")
            st.experimental_rerun()
        else:
            st.error("All fields required")

def main():
    if not st.session_state.user:
        show_login()
        return
    show_logout()
    user_id = st.session_state.user["id"]
    choice = main_menu()

    if choice == "ChatGPT Research":
        chatg
