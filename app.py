import streamlit as st

# Placeholder functions
def ask_ai(question, context=""):
    return f"AI answer to: '{question}'"

def quiz_multiple_flashcards():
    st.info("🧠 Flashcard 1: What is insulin?")
    st.info("💡 Flashcard 2: Name 3 signs of appendicitis")

def view_study_goals():
    st.info("🎯 1. Revise cardiology")
    st.info("🎯 2. Watch surgery OSCE video")

def run_osce_simulator():
    st.warning("OSCE simulator launching soon!")

def log_mood():
    st.success("Your mood has been logged!")

def show_daily_quote():
    st.info("🌞 'Success is the sum of small efforts repeated every day.'")

def run_clinical_simulation():
    st.info("🧪 Case: 45-year-old male with chest pain...")

def save_progress():
    st.success("✅ Your progress has been saved!")

def load_progress():
    st.success("📤 Loaded saved progress!")

def show_study_goals_calendar():
    st.info("📅 Upcoming: Revise pathology on Saturday.")

# App UI
st.set_page_config(page_title="Clinical AI Assistant")
st.title("🩺 Clinical AI Assistant")

menu = [
    "Ask Medical Question",
    "Start Flashcard Quiz",
    "View Study Goals",
    "Run OSCE Simulation",
    "Track Mood",
    "Daily Motivational Quote",
    "Clinical Simulation",
    "Save & Load Progress",
    "View Study Calendar"
]
choice = st.selectbox("📋 Main Menu", menu)

if choice == "Ask Medical Question":
    question = st.text_input("💬 Enter your medical question:")
    if st.button("Ask"):
        answer = ask_ai(question)
        st.success("🧠 " + answer)

elif choice == "Start Flashcard Quiz":
    quiz_multiple_flashcards()

elif choice == "View Study Goals":
    view_study_goals()

elif choice == "Run OSCE Simulation":
    run_osce_simulator()

elif choice == "Track Mood":
    log_mood()

elif choice == "Daily Motivational Quote":
    show_daily_quote()

elif choice == "Clinical Simulation":
    run_clinical_simulation()

elif choice == "Save & Load Progress":
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save"):
            save_progress()
    with col2:
        if st.button("📤 Load"):
            load_progress()

elif choice == "View Study Calendar":
    show_study_goals_calendar()
