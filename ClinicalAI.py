# app.py
# Clinical AI Assistant - single-file Streamlit app
# Features: menu/navigation, ChatGPT external button, quizzes, flashcards,
# daily check-ins, motivational quotes, study charts, planner/reminders, mnemonics,
# bank vault notes, basic signup/signin (no AI integration)

import streamlit as st
import sqlite3
import os
import json
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

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

# CRUD helpers for quizzes, flashcards, checkins, quotes, reminders, mnemonics, vault_notes (similar to previous, omitted for brevity, add if needed)

# -----------------------
# Login/signup UI (your exact code integrated)
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
# Main app UI
# -----------------------
def main():
    st.set_page_config(page_title="Clinical AI Assistant", layout="wide")

    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    if not st.session_state.user_id:
        show_login()
        return

    user_id = st.session_state.user_id

    menu = [
        "Home","ChatGPT (external)","Quizzes","Flashcards",
        "Daily Check-in","Quotes","Study Planner","Study Charts",
        "Mnemonics","Bank Vaults","Settings"
    ]
    page = st.sidebar.radio("Navigate", menu)

    st.sidebar.markdown(f"**Signed in as:** {user_id}")
    if st.sidebar.button("Sign out"):
        st.session_state.user_id = None
        st.experimental_rerun()

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
        # Example: list quizzes for user
        c = conn.cursor()
        c.execute("SELECT id,title,data FROM quizzes WHERE user_id=?", (user_id,))
        quizzes = c.fetchall()
        for qid, title, data_json in quizzes:
            st.subheader(title)
            try:
                data = json.loads(data_json)
                for i, item in enumerate(data):
                    st.write(f"Q{i+1}: {item.get('question','')}")
                    options = item.get('options', [])
                    for o in options:
                        st.write(f"- {o}")
                    st.write(f"Answer: {item.get('answer','')}")
            except Exception as e:
                st.error(f"Error loading quiz data: {e}")
            if st.button(f"Delete Quiz: {title}", key=f"del_{qid}"):
                c.execute("DELETE FROM quizzes WHERE id=? AND user_id=?", (qid, user_id))
                conn.commit()
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
                qid = str(uuid.uuid4())
                c.execute("INSERT INTO quizzes (id,user_id,title,data,created_at) VALUES (?,?,?,?,?)",
                          (qid, user_id, title, json.dumps(data_json), now_iso()))
                conn.commit()
                st.success("Quiz added.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Invalid JSON or error: {e}")

    elif page == "Flashcards":
        st.header("Flashcards")
        c = conn.cursor()
        c.execute("SELECT id,front,back FROM flashcards WHERE user_id=?", (user_id,))
        flashcards = c.fetchall()
        for fid, front, back in flashcards:
            st.write(f"**{front}** — {back}")
        st.markdown("### Add Flashcard")
        front = st.text_input("Front")
        back = st.text_input("Back")
        if st.button("Add Flashcard"):
            if front and back:
                fid = str(uuid.uuid4())
                c.execute("INSERT INTO flashcards (id,user_id,front,back,created_at) VALUES (?,?,?,?,?)",
                          (fid, user_id, front, back, now_iso()))
                conn.commit()
                st.success("Flashcard added.")
                st.experimental_rerun()
            else:
                st.error("Please enter both front and back.")

    elif page == "Daily Check-in":
        st.header("Daily Check-in")
        today_str = datetime.today().strftime("%Y-%m-%d")
        mood = st.selectbox("Mood", ["Happy", "Neutral", "Sad", "Tired", "Anxious"])
        focus = st.slider("Focus (1-10)", 1, 10, 5)
        hours = st.number_input("Hours studied", min_value=0.0, max_value=24.0, step=0.25)
        notes = st.text_area("Notes")
        if st.button("Add Check-in"):
            cid = str(uuid.uuid4())
            c = conn.cursor()
            c.execute("INSERT INTO checkins (id,user_id,date,mood,focus,hours,notes,created_at) VALUES (?,?,?,?,?,?,?,?)",
                      (cid, user_id, today_str, mood, focus, hours, notes, now_iso()))
            conn.commit()
            st.success("Check-in added.")
            st.experimental_rerun()
        st.markdown("### Past Check-ins")
        c = conn.cursor()
        c.execute("SELECT date,mood,focus,hours,notes FROM checkins WHERE user_id=? ORDER BY date DESC LIMIT 10", (user_id,))
        checkins = c.fetchall()
        for date, mood, focus, hours, notes in checkins:
            st.write(f"**{date}** — Mood: {mood}, Focus: {focus}, Hours: {hours}")
            st.write(f"Notes: {notes}")

    elif page == "Quotes":
        st.header("Motivational Quotes")
        c = conn.cursor()
        c.execute("SELECT id,quote,author FROM quotes WHERE user_id=?", (user_id,))
        quotes = c.fetchall()
        for qid, quote, author in quotes:
            st.write(f"\"{quote}\" — {author}")
        st.markdown("### Add Quote")
        quote = st.text_input("Quote")
        author = st.text_input("Author")
        if st.button("Add Quote"):
            if quote:
                qid = str(uuid.uuid4())
                c.execute("INSERT INTO quotes (id,user_id,quote,author,created_at) VALUES (?,?,?,?,?)",
                          (qid, user_id, quote, author, now_iso()))
                conn.commit()
                st.success("Quote added.")
                st.experimental_rerun()
            else:
                st.error("Quote cannot be empty.")

    elif page == "Study Planner":
        st.header("Study Planner (Reminders)")
        c = conn.cursor()
        c.execute("SELECT id,title,remind_at,notes FROM reminders WHERE user_id=? ORDER BY remind_at ASC", (user_id,))
        reminders = c.fetchall()
        for rid, title, remind_at, notes in reminders:
            st.write(f"**{title}** — Remind at: {remind_at}")
            st.write(f"Notes: {notes}")
        st.markdown("### Add Reminder")
        title = st.text_input("Title", key="reminder_title")
        remind_at = st.text_input("Remind at (YYYY-MM-DD HH:MM)", key="reminder_time")
        notes = st.text_area("Notes", key="reminder_notes")
        if st.button("Add Reminder"):
            if title and remind_at:
                rid = str(uuid.uuid4())
                c.execute("INSERT INTO reminders (id,user_id,title,remind_at,notes,created_at) VALUES (?,?,?,?,?,?)",
                          (rid, user_id, title, remind_at, notes, now_iso()))
                conn.commit()
                st.success("Reminder added.")
                st.experimental_rerun()
            else:
                st.error("Title and Remind at time are required.")

    elif page == "Study Charts":
        st.header("Study Charts")
        # You can add matplotlib or plotly charts here based on user data (like checkins)
        st.info("Feature coming soon!")

    elif page == "Mnemonics":
        st.header("Mnemonics")
        c = conn.cursor()
        c.execute("SELECT id,course,topic,name,content FROM mnemonics WHERE user_id=?", (user_id,))
        mnemonics = c.fetchall()
        for mid, course, topic, name, content in mnemonics:
            st.write(f"**{name}** ({course} - {topic}): {content}")
        st.markdown("### Add Mnemonic")
        course = st.selectbox("Course", SUBJECTS)
        topic = st.text_input("Topic")
        name = st.text_input("Mnemonic Name")
        content = st.text_area("Mnemonic Content")
        if st.button("Add Mnemonic"):
            if course and topic and name and content:
                mid = str(uuid.uuid4())
                c.execute("INSERT INTO mnemonics (id,user_id,course,topic,name,content
