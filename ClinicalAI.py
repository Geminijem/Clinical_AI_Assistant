# clinical_ai_assistant.py
import streamlit as st
from streamlit.components.v1 import components
import sqlite3
import os
import json
import uuid
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import matplotlib.pyplot as plt

# Encryption libs
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Configuration
DB_PATH = "app_data.db"
SUBJECTS = [
    "Pharmacology", "Microbiology", "Hematology", "Pathology", "Forensic Medicine",
    "Obstetrics and Gynecology", "Pediatrics", "Community and Public Medicine"
]

# Database initialization
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL,
        verified INTEGER DEFAULT 0,
        verification_token TEXT,
        reset_token TEXT,
        vault_salt TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS quizzes (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        data TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        front TEXT,
        back TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
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
    c.execute("""CREATE TABLE IF NOT EXISTS quotes (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        quote TEXT,
        author TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        title TEXT,
        remind_at TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
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

# Utility functions
def now_iso():
    return datetime.utcnow().isoformat()

def gen_token(nbytes=18):
    return base64.urlsafe_b64encode(os.urandom(nbytes)).decode()

# Auth helpers
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
    c.execute("SELECT id,password_hash,verified FROM users WHERE email=?", (email,))
    r = c.fetchone()
    if not r:
        return None
    uid, pw_hash, verified = r
    if check_password_hash(pw_hash, password):
        return {"id": uid, "verified": bool(verified)}
    return None

def set_verification_token(uid):
    token = gen_token()
    c = conn.cursor()
    c.execute("UPDATE users SET verification_token=?, verified=0 WHERE id=?", (token, uid))
    conn.commit()
    return token

def verify_token(token):
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE verification_token=?", (token,))
    r = c.fetchone()
    if not r:
        return None
    uid = r[0]
    c.execute("UPDATE users SET verified=1, verification_token=NULL WHERE id=?", (uid,))
    conn.commit()
    return uid

def request_reset_token(email):
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    r = c.fetchone()
    if not r:
        return None
    uid = r[0]
    token = gen_token()
    c.execute("UPDATE users SET reset_token=? WHERE id=?", (token, uid))
    conn.commit()
    return token

def perform_password_reset(token, new_password):
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE reset_token=?", (token,))
    r = c.fetchone()
    if not r:
        return None
    uid = r[0]
    pw_hash = generate_password_hash(new_password)
    c.execute("UPDATE users SET password_hash=?, reset_token=NULL WHERE id=?", (pw_hash, uid))
    conn.commit()
    return uid

# Encryption helpers (Fernet + PBKDF2)
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000, backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_to_b64(password: str, plaintext: str, salt: bytes) -> str:
    key = derive_key(password, salt)
    f = Fernet(key)
    token = f.encrypt(plaintext.encode())
    return base64.b64encode(token).decode()

def decrypt_from_b64(password: str, b64token: str, salt: bytes) -> str:
    key = derive_key(password, salt)
    f = Fernet(key)
    token = base64.b64decode(b64token)
    return f.decrypt(token).decode()

# CRUD helpers (quizzes, flashcards, checkins, quotes, reminders, mnemonics, vault)
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

def delete_flashcard(fid, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM flashcards WHERE id=? AND user_id=?", (fid, user_id))
    conn.commit()

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
        c.execute("SELECT id,subject,title,content,encrypted,created_at FROM vault_notes WHERE user_id=? AND subject=?", (user_id, subject))
    else:
        c.execute("SELECT id,subject,title,content,encrypted,created_at FROM vault_notes WHERE user_id=?", (user_id,))
    return [{'id': r[0], 'subject': r[1], 'title': r[2], 'content': r[3], 'encrypted': r[4], 'created_at': r[5]} for r in c.fetchall()]

# Voice widget (Web Speech API)
VOICE_COMPONENT_HTML = '''
<div>
  <button id="startBtn">🎤 Start Voice Input</button>
  <div id="transcript" style="white-space:pre-wrap;margin-top:6px;"></div>
  <script>
    const start = document.getElementById('startBtn');
    const transcript = document.getElementById('transcript');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      transcript.innerText = 'Voice recognition not supported in this browser.';
    } else {
      const r = new SpeechRecognition();
      r.interimResults = true;
      r.lang = 'en-US';
      r.onresult = (ev) => {
        let full = '';
        for (let i = ev.resultIndex; i <
