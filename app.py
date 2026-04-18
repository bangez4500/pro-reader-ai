import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import spacy
from PIL import Image
import io

# --- NLP MODELLERİNİ YÜKLE ---
@st.cache_resource
def load_nlp_models():
    # Bu modeller requirements.txt üzerinden otomatik kurulduğu için direkt çağırıyoruz
    return {
        "fr": spacy.load("fr_core_news_sm"),
        "en": spacy.load("en_core_web_sm")
    }

nlp_models = load_nlp_models()

# --- RENKLENDİRME FONKSİYONU ---
def highlight_grammar(text, lang_code):
    if lang_code not in nlp_models or nlp_models[lang_code] is None:
        return text
    
    doc = nlp_models[lang_code](text)
    html_output = ""
    for token in doc:
        color = "#1a1a1a" 
        if token.pos_ == "VERB": color = "#e67e22" # Turuncu
        elif token.pos_ == "NOUN": color = "#2980b9" # Mavi
        elif token.pos_ == "ADJ": color = "#27ae60" # Yeşil
            
        html_output += f'<span style="color:{color}; font-weight: 500;">{token.text}</span> '
    return html_output

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Reader AI", layout="wide", initial_sidebar_state="collapsed")

# --- CSS TASARIM ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 1rem !important; }
    .reading-box {
        background-color: #ffffff; padding: 30px; border-radius: 12px;
        border: 1px solid #e1e4e8; font-family: 'Georgia', serif;
        line-height: 1.8; font-size: 1.2rem; color: #1a1a1a; margin-bottom: 20px;
    }
    .para-block { margin-bottom: 22px; display: block; }
    .lang-label { font-weight: bold; font-size: 0.8rem; color: #555; margin-bottom: 10px; display: block; border-left: 4px solid #1f77b4; padding-left: 10px; }
    .stButton > button { height: 48px !important; background-color: #1f77b4 !important; color: white !important; width: 100%; border-radius: 10px; }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- PANEL ---
h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.5, 2, 0.7, 0.7, 1])
with h_col1: st.markdown("<h3 style='margin:0; color:#1f77b4;'>📖 Pro Reader AI</h3>", unsafe_allow_html=True)
with h_col2: uploaded_file = st.file_uploader("PDF", type="pdf", label_visibility="collapsed")

if uploaded_file:
    if "last_file_id" not in st.session_state or st.session_state.last_file_id != uploaded_file.name:
        st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        st.session_state.last_file_id = uploaded_file.name
        st.session_state.pop('last_fr', None)
        st.session_state.pop('last_en', None)
        st.rerun()

    doc = st.session_state.pdf_doc
    with h_col3: page_num = st.number_input("P", 1, len(doc), 1, key="pg", label_visibility="collapsed")
    with h_col4: focus_mode = st.toggle("Focus", value=True)
    with h_col5: analyze_btn = st.button("🔍 Analiz Et")

    st.divider()

    page = doc[page_num - 1]
    if analyze_btn:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        to_fr, to_en = GoogleTranslator(source='auto', target='fr'), GoogleTranslator(source='auto', target='en')
        fr_html, en_html = "", ""
        with st.spinner("Analiz ediliyor..."):
            for b in blocks:
                text = b[4].strip()
                if b[6] == 0 and len(text) > 2:
                    raw_fr, raw_en = to_fr.translate(text), to_en.translate(text)
                    fr_html += f'<div class="para-block">{highlight_grammar(raw_fr, "fr")}</div>'
                    en_html += f'<div class="para-block">{highlight_grammar(raw_en, "en")}</div>'
        st.session_state.last_fr, st.session_state.last_en = fr_html, en_html

    if focus_mode:
        c1, c2 = st.columns([1, 1])
        with c1: 
            st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA</span>', unsafe_allow_html=True)
            if 'last_fr' in st.session_state: st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
        with c2: 
            st.markdown('<span class="lang-label">🇬🇧 İNGİLİZCE</span>', unsafe_allow_html=True)
            if 'last_en' in st.session_state: st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([1, 1])
        with c1: st.image(Image.open(io.BytesIO(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes())), use_container_width=True)
        with c2:
            if 'last_fr' in st.session_state:
                st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
else:
    st.info("PDF yükleyerek başla.")
