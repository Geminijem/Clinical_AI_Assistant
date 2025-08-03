import streamlit as st
from transformers import AutoTokenizer, AutoModelForQuestionAnswering
import torch
from ddgs import DDGS
from gtts import gTTS
import os
import tempfile

# Load model and tokenizer once on app start
@st.cache_resource(show_spinner=False)
def load_model():
    tokenizer = AutoTokenizer.from_pretrained("deepset/roberta-base-squad2")
    model = AutoModelForQuestionAnswering.from_pretrained("deepset/roberta-base-squad2")
    return tokenizer, model

tokenizer, model = load_model()

clinical_context = """
Pancreatitis is inflammation of the pancreas. Common symptoms include abdominal pain, nausea, vomiting.
The sinoatrial node is the natural pacemaker of the heart.
Diabetes mellitus is a chronic condition characterized by high blood sugar levels.
"""  # Expand this as needed

def ask_ai(question, context=clinical_context):
    inputs = tokenizer.encode_plus(question, context, return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    start = torch.argmax(outputs.start_logits)
    end = torch.argmax(outputs.end_logits) + 1
    answer_tokens = inputs["input_ids"][0][start:end]
    answer = tokenizer.decode(answer_tokens, skip_special_tokens=True)

    if len(answer.strip()) < 3 or answer.lower() in ["[cls]", "[sep]", ""]:
        return None
    return answer.strip()

def search_online(query):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=1)
            for r in results:
                snippet = r.get("body") or r.get("snippet") or r.get("content")
                if snippet:
                    return snippet.strip()
        return None
    except Exception:
        return None

def get_answer(question):
    answer = ask_ai(question)
    if answer:
        return f"🧠 Local AI answer:\n{answer}"
    online_answer = search_online(question)
    if online_answer:
        return f"🌐 Online search answer:\n{online_answer}"
    return "❌ Sorry, I couldn't find an answer."

# --- Streamlit UI ---

st.set_page_config(page_title="Clinical AI Assistant")
st.title("🩺 Clinical AI Assistant")

st.markdown(
    """
    <script>
    const sleep = (delay) => new Promise((resolve) => setTimeout(resolve, delay));
    // Voice input function
    async function record() {
        var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'en-US';
        recognition.start();

        recognition.onresult = function(event) {
            let transcript = event.results[0][0].transcript;
            document.getElementById('voice_input').value = transcript;
            const el = new Event('input', { bubbles: true });
            document.getElementById('voice_input').dispatchEvent(el);
        };
    }
    </script>
    <style>
    #voice_button {
        margin-top: 10px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Text input with voice input button
st.text_input("💬 Ask a clinical question:", key="voice_input")
st.button("🎤 Speak", on_click=st.components.v1.html("record();", height=0, width=0, key="js"))

question = st.session_state.get("voice_input", "").strip()

if st.button("Get Answer") and question:
    with st.spinner("Thinking..."):
        response = get_answer(question)
    st.success(response)

    # Text-to-speech output
    tts = gTTS(text=response, lang='en')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tts.save(tmp_file.name)
        audio_file = tmp_file.name
    audio_bytes = open(audio_file, 'rb').read()
    st.audio(audio_bytes, format='audio/mp3')
    os.unlink(audio_file)
else:
    st.info("Type your question or use the 🎤 Speak button, then press Get Answer.")

st.caption("Built with free AI models and DuckDuckGo search — no OpenAI required.")
