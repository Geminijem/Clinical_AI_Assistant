#Clinical AI Assistant - Single-file Streamlit app

#Filename: app.py

#Purpose: Minimal, debugged, single-file Streamlit app implementing

#- Sidebar menu/navigation

#- Authentication (signup/signin) with SQLite (email + password)

#- AI section (text + voice I/O using Web Speech API via a custom component)

#- Editable Quizzes (CRUD)

#- Editable Flashcards (CRUD)

#- Daily Check-in (mood, focus, hours, notes)

#- Daily Medical Motivational Quotes (editable)

#- Study Charts (from check-ins)

#- Study Planner with reminder alerts (in-browser scheduled notifications)

#- Editable Mnemonics section

#- Bank vaults for medical notes (per subject)

#Notes: This is a single-file workable prototype tailored for Android browsers.

#It uses SQLite for persistence and streamlit.components.v1 for small JS integration.

import streamlit as st from streamlit.components.v1 
import components 
import sqlite3 from werkzeug.security 
import generate_password_hash, check_password_hash 
import pandas as pd 
import matplotlib.pyplot as plt from datetime 
import datetime, timedelta 
import uuid 
import json

#-----------------------

#DATABASE HELPERS

#-----------------------

DB_PATH = 'app_data.db'

def get_conn(): conn = sqlite3.connect(DB_PATH, check_same_thread=False) conn.execute("PRAGMA foreign_keys = ON;") return conn

def init_db(): conn = get_conn() c = conn.cursor() # users c.execute(''' CREATE TABLE IF NOT EXISTS users ( id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL ) ''') # quizzes c.execute(''' CREATE TABLE IF NOT EXISTS quizzes ( id TEXT PRIMARY KEY, user_id TEXT, title TEXT, data TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # flashcards c.execute(''' CREATE TABLE IF NOT EXISTS flashcards ( id TEXT PRIMARY KEY, user_id TEXT, front TEXT, back TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # checkins c.execute(''' CREATE TABLE IF NOT EXISTS checkins ( id TEXT PRIMARY KEY, user_id TEXT, date TEXT, mood TEXT, focus INTEGER, hours REAL, notes TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # quotes c.execute(''' CREATE TABLE IF NOT EXISTS quotes ( id TEXT PRIMARY KEY, user_id TEXT, quote TEXT, author TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # planner c.execute(''' CREATE TABLE IF NOT EXISTS reminders ( id TEXT PRIMARY KEY, user_id TEXT, title TEXT, remind_at TEXT, notes TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # mnemonics c.execute(''' CREATE TABLE IF NOT EXISTS mnemonics ( id TEXT PRIMARY KEY, user_id TEXT, course TEXT, topic TEXT, name TEXT, content TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') # bank vaults: subject + notes c.execute(''' CREATE TABLE IF NOT EXISTS vault_notes ( id TEXT PRIMARY KEY, user_id TEXT, subject TEXT, title TEXT, content TEXT, created_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ''') conn.commit() return conn

conn = init_db()

#-----------------------

#AUTH HELPERS

#-----------------------

def signup(email, password): c = conn.cursor() user_id = str(uuid.uuid4()) pw_hash = generate_password_hash(password) try: c.execute('INSERT INTO users (id,email,password_hash,created_at) VALUES (?,?,?,?)', (user_id, email, pw_hash, datetime.utcnow().isoformat())) conn.commit() return user_id except sqlite3.IntegrityError: return None

def login(email, password): c = conn.cursor() c.execute('SELECT id,password_hash FROM users WHERE email=?', (email,)) row = c.fetchone() if not row: return None user_id, pw_hash = row if check_password_hash(pw_hash, password): return user_id return None

#-----------------------

#SMALL UTILITIES

#-----------------------

def now(): return datetime.utcnow().isoformat()

#-----------------------

#JAVASCRIPT VOICE I/O COMPONENT

#-----------------------

VOICE_COMPONENT_HTML = """

<div>
  <button id="startBtn">🎤 Start Voice Input</button>
  <button id="stopBtn">⏹ Stop</button>
  <div id="transcript"></div>
  <script>
  const start = document.getElementById('startBtn');
  const stop = document.getElementById('stopBtn');
  const transcript = document.getElementById('transcript');// Speech Recognition (may not work in all browsers) const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition; if (!SpeechRecognition) { transcript.innerText = 'Voice recognition not supported in this browser.'; } else { const recog = new SpeechRecognition(); recog.interimResults = true; recog.lang = 'en-US'; let finalTranscript = ''; recog.onresult = (ev) => { let interim = ''; for (let i=ev.resultIndex;i<ev.results.length;i++){ const t = ev.results[i][0].transcript; if (ev.results[i].isFinal) finalTranscript += t; else interim += t; } transcript.innerText = finalTranscript + '\n' + interim; // send to Streamlit if (finalTranscript) { const payload = {text: finalTranscript}; // post message to Streamlit via event window.parent.postMessage({streamlitVoice: payload}, '*'); } } start.onclick = ()=>{recog.start();} stop.onclick = ()=>{recog.stop();} }

// function to speak text function speak(text) { if ('speechSynthesis' in window) { const u = new SpeechSynthesisUtterance(text); window.speechSynthesis.speak(u); } }

// listen for messages from Streamlit to speak window.addEventListener('message', (e)=>{ try { if (e.data && e.data.type === 'speak') { speak(e.data.text || ''); } } catch (err) {console.warn(err)} }) </script>

</div>
"""Helper to render component and capture events

def voice_component(): components.html(VOICE_COMPONENT_HTML, height=180) # capture window.postMessage - Streamlit can't directly capture, but we can instruct user to paste transcript st.info('If your browser supports it, click Start and allow microphone access. Final transcript will be posted to the browser console — copy/paste into the assistant input below if automatic capture is blocked by your browser.')

Helper to trigger speech from Python -> JS

def speak_client(text): # we send a small html snippet that posts a message to the frame to trigger the speech function speak_html = f""" <script> window.postMessage({json.dumps({'type':'speak','text':text})}, '*'); </script> """ components.html(speak_html, height=0)

-----------------------

CRUD helpers (quizzes, flashcards, etc.)

-----------------------

def insert_quiz(user_id, title, data_json): c = conn.cursor() qid = str(uuid.uuid4()) c.execute('INSERT INTO quizzes (id,user_id,title,data,created_at) VALUES (?,?,?,?,?)', (qid, user_id, title, json.dumps(data_json), now())) conn.commit()

def list_quizzes(user_id): c = conn.cursor() c.execute('SELECT id,title,data,created_at FROM quizzes WHERE user_id=?', (user_id,)) rows = c.fetchall() return [{'id':r[0],'title':r[1],'data':json.loads(r[2]),'created_at':r[3]} for r in rows]

def delete_quiz(qid, user_id): c = conn.cursor() c.execute('DELETE FROM quizzes WHERE id=? AND user_id=?', (qid, user_id)) conn.commit()

flashcards

def add_flashcard(user_id, front, back): c = conn.cursor() fid = str(uuid.uuid4()) c.execute('INSERT INTO flashcards (id,user_id,front,back,created_at) VALUES (?,?,?,?,?)', (fid, user_id, front, back, now())) conn.commit()

def list_flashcards(user_id): c = conn.cursor() c.execute('SELECT id,front,back,created_at FROM flashcards WHERE user_id=?', (user_id,)) return [{'id':r[0],'front':r[1],'back':r[2],'created_at':r[3]} for r in c.fetchall()]

def delete_flashcard(fid, user_id): c = conn.cursor() c.execute('DELETE FROM flashcards WHERE id=? AND user_id=?', (fid, user_id)) conn.commit()

checkins

def add_checkin(user_id, date, mood, focus, hours, notes): c = conn.cursor() cid = str(uuid.uuid4()) c.execute('INSERT INTO checkins (id,user_id,date,mood,focus,hours,notes,created_at) VALUES (?,?,?,?,?,?,?,?)', (cid,user_id,date,mood,focus,hours,notes, now())) conn.commit()

def list_checkins(user_id): c = conn.cursor() c.execute('SELECT id,date,mood,focus,hours,notes,created_at FROM checkins WHERE user_id=? ORDER BY date ASC', (user_id,)) rows = c.fetchall() return [{'id':r[0],'date':r[1],'mood':r[2],'focus':r[3],'hours':r[4],'notes':r[5],'created_at':r[6]} for r in rows]

quotes

def add_quote(user_id, quote, author=''): c = conn.cursor() qid = str(uuid.uuid4()) c.execute('INSERT INTO quotes (id,user_id,quote,author,created_at) VALUES (?,?,?,?,?)', (qid,user_id,quote,author, now())) conn.commit()

def list_quotes(user_id): c = conn.cursor() c.execute('SELECT id,quote,author,created_at FROM quotes WHERE user_id=?', (user_id,)) return [{'id':r[0],'quote':r[1],'author':r[2],'created_at':r[3]} for r in c.fetchall()]

reminders

def add_reminder(user_id, title, remind_at, notes=''): c = conn.cursor() rid = str(uuid.uuid4()) c.execute('INSERT INTO reminders (id,user_id,title,remind_at,notes,created_at) VALUES (?,?,?,?,?,?)', (rid,user_id,title,remind_at,notes, now())) conn.commit()

def list_reminders(user_id): c = conn.cursor() c.execute('SELECT id,title,remind_at,notes,created_at FROM reminders WHERE user_id=? ORDER BY remind_at ASC', (user_id,)) return [{'id':r[0],'title':r[1],'remind_at':r[2],'notes':r[3],'created_at':r[4]} for r in c.fetchall()]

mnemonics

def add_mnemonic(user_id, course, topic, name, content): c = conn.cursor() mid = str(uuid.uuid4()) c.execute('INSERT INTO mnemonics (id,user_id,course,topic,name,content,created_at) VALUES (?,?,?,?,?,?,?)', (mid,user_id,course,topic,name,content, now())) conn.commit()

def list_mnemonics(user_id): c = conn.cursor() c.execute('SELECT id,course,topic,name,content,created_at FROM mnemonics WHERE user_id=?', (user_id,)) return [{'id':r[0],'course':r[1],'topic':r[2],'name':r[3],'content':r[4],'created_at':r[5]} for r in c.fetchall()]

vault notes

SUBJECTS = ['Pharmacology','Microbiology','Hematology','Pathology','Forensic Medicine','Obstetrics and Gynecology','Pediatrics','Community and Public Medicine']

def add_vault_note(user_id, subject, title, content): if subject not in SUBJECTS: raise ValueError('Unknown subject') c = conn.cursor() vid = str(uuid.uuid4()) c.execute('INSERT INTO vault_notes (id,user_id,subject,title,content,created_at) VALUES (?,?,?,?,?,?)', (vid,user_id,subject,title,content, now())) conn.commit()

def list_vault_notes(user_id, subject=None): c = conn.cursor() if subject: c.execute('SELECT id,subject,title,content,created_at FROM vault_notes WHERE user_id=? AND subject=?', (user_id,subject)) else: c.execute('SELECT id,subject,title,content,created_at FROM vault_notes WHERE user_id=?', (user_id,)) return [{'id':r[0],'subject':r[1],'title':r[2],'content':r[3],'created_at':r[4]} for r in c.fetchall()]

-----------------------

APP UI

-----------------------

st.set_page_config(page_title='Clinical AI Assistant', layout='wide')

SESSION: store user id

if 'user_id' not in st.session_state: st.session_state.user_id = None

--- Authentication ---

with st.sidebar: st.title('Clinical AI Assistant') if st.session_state.user_id is None: auth_choice = st.radio('Account', ['Sign in','Sign up','Guest'], index=0) if auth_choice == 'Sign up': st.subheader('Create account') su_email = st.text_input('Email', key='su_email') su_password = st.text_input('Password', type='password', key='su_pw') if st.button('Create account'): uid = signup(su_email, su_password) if uid: st.success('Account created — signed in') st.session_state.user_id = uid else: st.error('Email already exists') elif auth_choice == 'Sign in': st.subheader('Sign in') in_email = st.text_input('Email', key='in_email') in_password = st.text_input('Password', type='password', key='in_pw') if st.button('Sign in'): uid = login(in_email, in_password) if uid: st.success('Signed in') st.session_state.user_id = uid else: st.error('Invalid credentials') else: if st.button('Continue as Guest'): st.session_state.user_id = 'guest' st.info('Guest mode - data will be local') else: st.markdown('Signed in') st.write(st.session_state.user_id) if st.button('Sign out'): st.session_state.user_id = None st.experimental_rerun()

Navigation menu

menu_items = ['Home','AI Assistant','Quizzes','Flashcards','Daily Check-in','Quotes','Study Planner','Study Charts','Mnemonics','Bank Vaults','Settings'] choice = st.sidebar.radio('Navigate', menu_items)

Home

if choice == 'Home': st.header('Welcome') st.write('This is a prototype Clinical AI Assistant. Use the sidebar to navigate.') st.info('Designed for Android browsers. For voice features, use Chrome on Android for best support.')

AI Assistant

if choice == 'AI Assistant': st.header('AI Assistant (local prototype)') st.write('This built-in assistant is a local prototype and does not require OpenAI keys. For deeper research, open the External ChatGPT button to use web ChatGPT in a new tab.') col1, col2 = st.columns([2,1]) with col1: user_input = st.text_area('Ask a question or paste voice transcript here') if st.button('Send to Assistant'): # Simple local assistant logic: search vault notes for matching keywords, else echo results = [] if st.session_state.user_id: notes = list_vault_notes(st.session_state.user_id) for n in notes: if user_input.lower() in (n['title']+n['content']).lower(): results.append(f"Found in {n['subject']}: {n['title']}\n{n['content'][:400]}") if results: reply = '\n\n---\n\n'.join(results) else: reply = "I don't have external model access. I can: 1) search your notes (done), or 2) open external ChatGPT/Gemini for deeper answers.\n\nEcho:\n" + user_input st.text_area('Assistant reply', value=reply, height=250) # speak if st.checkbox('Enable voice reply (speak)'): speak_client(reply) with col2: st.subheader('Voice Input') st.markdown('Use the voice widget below. If browser blocks automatic postMessage events, copy the transcript into the assistant input box.') voice_component() st.markdown('---') st.subheader('External models') st.write('Open external chat services in a new tab:') if st.button('Open ChatGPT (web)'): js = "window.open('https://chat.openai.com','_blank')" components.html(f"<script>{js}</script>", height=0) if st.button('Open Gemini (web)'): js = "window.open('https://gemini.google.com','_blank')" components.html(f"<script>{js}</script>", height=0)

Quizzes

if choice == 'Quizzes': st.header('Quizzes (editable)') if not st.session_state.user_id: st.warning('Please sign in or continue as Guest to use quizzes.') else: with st.expander('Create new quiz'): q_title = st.text_input('Quiz title') q_data_raw = st.text_area('Quiz JSON (list of {question,options,answer})','[\n  {"question":"What is...","options":["A","B"],"answer":0}\n]') if st.button('Save quiz'): try: parsed = json.loads(q_data_raw) insert_quiz(st.session_state.user_id, q_title, parsed) st.success('Saved') except Exception as e: st.error('Invalid JSON: ' + str(e)) st.subheader('Your quizzes') quizzes = list_quizzes(st.session_state.user_id) for q in quizzes: st.markdown(f"{q['title']} — {q['created_at']}") if st.button('Delete', key='del_'+q['id']): delete_quiz(q['id'], st.session_state.user_id) st.experimental_rerun() if st.button('Take quiz', key='take_'+q['id']): # simple quiz runner st.session_state['current_quiz'] = q st.experimental_rerun() if 'current_quiz' in st.session_state and st.session_state['current_quiz']: q = st.session_state['current_quiz'] st.markdown('### Taking: ' + q['title']) score = 0 for i, item in enumerate(q['data']): st.write(f"Q{i+1}: {item.get('question','')}") choice_idx = st.radio(f'Choose (Q{i})', item.get('options',[]), key=f'q{q["id"]}{i}') if st.button('Submit answers'): # naive check for j, itm in enumerate(q['data']): sel = st.session_state.get(f'q{q["id"]}{j}') if isinstance(sel, int): if sel == itm.get('answer'): score += 1 else: try: if item.get('options').index(sel) == itm.get('answer'): score += 1 except Exception: pass st.success(f'Score: {score} / {len(q["data"])}') del st.session_state['_current_quiz'] st.experimental_rerun()

Flashcards

if choice == 'Flashcards': st.header('Flashcards (editable)') if not st.session_state.user_id: st.warning('Sign in or continue as Guest to use flashcards.') else: with st.form('add_flash'): f_front = st.text_input('Front') f_back = st.text_area('Back') if st.form_submit_button('Add flashcard'): add_flashcard(st.session_state.user_id, f_front, f_back) st.success('Added') st.markdown('---') fcards = list_flashcards(st.session_state.user_id) for f in fcards: st.markdown(f"{f['front']} — {f['created_at']}") if st.button('Show back', key='show_'+f['id']): st.write(f['back']) if st.button('Delete', key='delf_'+f['id']): delete_flashcard(f['id'], st.session_state.user_id) st.experimental_rerun()

Daily Check-in

if choice == 'Daily Check-in': st.header('Daily Check-in') if not st.session_state.user_id: st.warning('Sign in or Guest only') else: with st.form('checkin'): date = st.date_input('Date', value=datetime.utcnow().date()) mood = st.selectbox('Mood',['Great','Good','Okay','Tired','Stressed']) focus = st.slider('Focus (1-10)', 1, 10, 6) hours = st.number_input('Hours Studied', 0.0, 24.0, 1.0, step=0.5) notes = st.text_area('Notes') if st.form_submit_button('Save check-in'): add_checkin(st.session_state.user_id, date.isoformat(), mood, focus, hours, notes) st.success('Saved') st.subheader('Past check-ins') ch = list_checkins(st.session_state.user_id) if ch: df = pd.DataFrame(ch) st.dataframe(df[['date','mood','focus','hours','notes']])

Quotes

if choice == 'Quotes': st.header('Daily Medical Motivational Quotes') if not st.session_state.user_id: st.warning('Sign in or Guest only') else: with st.form('add_quote'): qquote = st.text_input('Quote') qauthor = st.text_input('Author') if st.form_submit_button('Add quote'): add_quote(st.session_state.user_id, qquote, qauthor) st.success('Added') # show random quotes = list_quotes(st.session_state.user_id) if quotes: import random q = random.choice(quotes) st.markdown(f"> {q['quote']} — {q['author']}") st.write('All quotes:') for qu in quotes: st.write(qu['quote'],'—',qu['author'])

Study Planner / Reminders

if choice == 'Study Planner': st.header('Study Planner / Reminders') if not st.session_state.user_id: st.warning('Sign in or Guest only') else: with st.form('add_rem'): title = st.text_input('Title') remind_at = st.datetime_input('Remind at', value=datetime.utcnow()+timedelta(minutes=1)) notes = st.text_area('Notes') if st.form_submit_button('Add reminder'): add_reminder(st.session_state.user_id, title, remind_at.isoformat(), notes) st.success('Added') st.subheader('Upcoming reminders') rems = list_reminders(st.session_state.user_id) for r in rems: st.write(r['title'], '-', r['remind_at'])

st.markdown('''
    **In-Browser Notification**: Click the button below to request browser notification permission. This prototype will only schedule notifications while the page is open in your browser tab (browser limitations).''')
    if st.button('Request Notification Permission'):
        components.html("""
        <script>
        Notification.requestPermission().then(function(p){
          if (p==='granted') alert('Notifications granted — reminders will trigger while this page is open.');
          else alert('Notifications denied.');
        })
        </script>
        """, height=0)
    # schedule upcoming reminders as simple setTimeouts for those within the next hour (demo)
    for r in rems:
        try:
            dt = datetime.fromisoformat(r['remind_at'])
            ms = int((dt - datetime.utcnow()).total_seconds()*1000)
            if ms > 0 and ms < 1000*60*60*24:  # within 24h
                components.html(f"""
                <script>
                setTimeout(()=>{new Notification({json.dumps(r['title'])});}, {ms});
                </script>
                """, height=0)
        except Exception:
            pass

Study Charts

if choice == 'Study Charts': st.header('Study Charts') if not st.session_state.user_id: st.warning('Sign in or Guest only') else: ch = list_checkins(st.session_state.user_id)
if not ch:
            st.info('No check-ins yet')
        else:
            df = pd.DataFrame(ch)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            fig, ax = plt.subplots()
            ax.plot(df['date'], df['hours'], marker='o')
            ax.set_xlabel('Date')
            ax.set_ylabel('Hours studied')
            ax.set_title('Hours over time')
            st.pyplot(fig)

# Mnemonics
if choice == 'Mnemonics':
    st.header('Editable Mnemonics')
    if not st.session_state.user_id:
        st.warning('Sign in or Guest only')
    else:
        with st.form('add_mn'):
            course = st.selectbox('Course',['Pharmacology','Pathology','Microbiology','Other'])
            topic = st.text_input('Topic')
            name = st.text_input('Mnemonic name')
            content = st.text_area('Mnemonic content')
            if st.form_submit_button('Add mnemonic'):
                add_mnemonic(st.session_state.user_id, course, topic, name, content)
                st.success('Saved')
        st.markdown('Your mnemonics:')
        mns = list_mnemonics(st.session_state.user_id)
        for m in mns:
            st.markdown(f"**{m['name']}** ({m['course']} — {m['topic']})")
            st.write(m['content'])

# Bank Vaults
if choice == 'Bank Vaults':
    st.header('Bank Vaults for Notes')
    if not st.session_state.user_id:
        st.warning('Sign in or Guest only')
    else:
        subj = st.selectbox('Subject', SUBJECTS)
        with st.form('add_note'):
            title = st.text_input('Title')
            content = st.text_area('Content (supports markdown)')
            if st.form_submit_button('Save note'):
                add_vault_note(st.session_state.user_id, subj, title, content)
                st.success('Saved')
        st.subheader('Notes in ' + subj)
        notes = list_vault_notes(st.session_state.user_id, subj)
        for n in notes:
            st.markdown(f"### {n['title']}")
            st.write(n['content'])

# Settings
if choice == 'Settings':
    st.header('Settings & Deployment Helper')
    st.markdown('**Where files go (for Sadiq):**')
    st.markdown('''
    - `app.py` -> root of your GitHub repository and Streamlit app
    - `requirements.txt` -> list required packages (see below)
    - `app_data.db` -> SQLite database will be created automatically in your app working directory
    - `README.md` -> instructions and deployment steps
    ''')
    st.markdown('**requirements.txt (suggested)**')
    st.code('''
    streamlit
    pandas
    matplotlib
    werkzeug
    ''')
    st.markdown('**Deploy to Streamlit Cloud**')
    st.markdown('''
    1. Create a GitHub repo and push `app.py` and `requirements.txt`.
    2. On Streamlit Cloud, create a new app and connect your GitHub repo; point to `app.py`.
    3. Deploy — Streamlit will install dependencies and run the app.

    Notes about Android/installable:
    - Open the Streamlit web URL in Chrome on Android. You can install it as a Progressive Web App (PWA) from Chrome's menu ("Install app") — this typically adds it to the launcher but does not require third-party apps.
    - Fully background reminders and offline notifications require Service Worker support and a PWA manifest (advanced). This prototype demonstrates in-tab notifications while the page is open.
    ''')
    st.markdown('**Security notes**')
    st.markdown('''
    - This simple auth uses hashed passwords in SQLite. For production, use a proper backend (Firebase/Auth0) and TLS.
    - Do NOT rely on this for high-security data. Consider encryption for vault notes if desired.
    ''')

# END

st.footer = st.write('\n---\nPrototype created for Sadiq. Modify and extend for production use.')
