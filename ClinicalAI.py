import streamlit as st
import sqlite3
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# --- Database Setup ---
DB_PATH = "app_data.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

conn = get_conn()

def init_db():
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

init_db()

# --- Auth functions ---

def create_user(email, password):
    c = conn.cursor()
    uid = str(uuid.uuid4())
    pw_hash = generate_password_hash(password)
    try:
        c.execute(
            "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (uid, email, pw_hash, datetime.utcnow().isoformat())
        )
        conn.commit()
        return uid
    except sqlite3.IntegrityError:
        return None

def authenticate(email, password):
    c = conn.cursor()
    c.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    if row:
        user_id, pw_hash = row
        if check_password_hash(pw_hash, password):
            return {"id": user_id}
    return None

# --- Login/signup UI ---

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
            user = authenticate(email, password)
            if user:
                st.session_state.user = user
                st.success("Signed in successfully")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials.")

    else:  # Guest
        if st.button("Continue as Guest"):
            st.session_state.user = {"id": "guest"}
            st.experimental_rerun()

# --- Main app ---

def main():
    if "user" not in st.session_state or st.session_state.user is None:
        show_login()
        return  # Don't run rest if not logged in

    user = st.session_state.user
    user_id = user.get("id", "guest")

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Profile", "Logout"])

    if page == "Home":
        st.header("Welcome to Clinical AI Assistant")
        st.write(f"Hello, user ID: {user_id}")
        # TODO: add your main app features here

    elif page == "Profile":
        st.header("User Profile")
        st.write(f"User ID: {user_id}")
        # TODO: profile details here

    elif page == "Logout":
        if st.button("Confirm Logout"):
            st.session_state.user = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()
