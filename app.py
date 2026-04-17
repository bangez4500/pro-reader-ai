import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import spacy
from PIL import Image
import io

# --- NLP MODELLERİNİ YÜKLE ---
@st.cache_resource
def load_nlp_models():
    try:
        return {
            "fr": spacy.load("fr_core_news_sm"),
            "en": spacy.load("en_core_web_sm")
        }
    except:
        return {}

nlp_models = load_nlp_models()

# --- RENKLENDİRME FONKSİYONU ---
def highlight_grammar(text, lang_code):
    if lang_code not in nlp_models or not nlp_models[lang_code]:
        return text
    doc = nlp_models[lang_code](text)
    html_output = ""
    for token in doc:
        color = "#1a1a1a"
        if token.pos_ == "VERB": color = "#e67e22" 
        elif token.pos_ == "NOUN": color = "#2980b9" 
        elif token.pos_ == "ADJ": color = "#27ae60" 
        html_output += f'<span style="color:{color};">{token.text}</span> '
    return html_output

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Reader AI", layout="wide", initial_sidebar_state="collapsed")

# --- TABLET OPTİMİZASYONLU CSS ---
st.markdown("""
    <style>
    /* Üst bar ve beyazlık giderme */
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 0.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }

    /* Dokunmatik dostu butonlar ve inputlar */
    .stButton > button {
        height: 45px !important;
        border-radius: 8px !important;
        font-size: 16px !important; /* Tablette daha rahat okunur */
        background-color: #1f77b4 !important;
    }
    
    /* Sayfa seçiciyi tablet için büyütme */
    div[data-testid="stNumberInput"] input {
        height: 45px !important;
        font-size: 18px !important;
    }

    /* Okuma Kutusu: Tablette metin ferahlığı */
    .reading-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #e0e4e8;
        font-family: 'Georgia', serif;
        line-height: 1.7;
        font-size: 1.2rem; /* Tablette göz yormasın */
        color: #1a1a1a;
        margin-bottom: 20px;
        -webkit-overflow-scrolling: touch; /* iOS kaydırma yumuşatma */
    }
    
    .para-block { margin-bottom: 22px; display: block; }
    
    /* Sidebar'ı her ihtimale karşı gizle */
    [data-testid="stSidebar"] { display: none; }

    /* Header Alanını Daraltma */
    .stHorizontalBlock { align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER (TABLET DÜZENİ) ---
head_col1, head_col2, head_col3, head_col4, head_col5 = st.columns([1.5, 2, 0.8, 0.8, 1])

with head_col1:
    st.markdown("<h3 style='margin:0; color:#1f77b4;'>📖 Pro Reader</h3>", unsafe_allow_html=True)

with head_col2:
    uploaded_file = st.file_uploader("Dosya Seç", type="pdf", label_visibility="collapsed")

# --- DOSYA VE SESSION KONTROLÜ ---
if uploaded_file:
    if "last_file_id" not in st.session_state or st.session_state.last_file_id != uploaded_file.name:
        st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        st.session_state.last_file_id = uploaded_file.name
        # Yeni kitapta eski verileri temizle
        keys_to_del = ['last_fr', 'last_en']
        for key in keys_to_del:
            if key in st.session_state: del st.session_state[key]
        st.rerun()

    doc = st.session_state.pdf_doc

    with head_col3:
        page_num = st.number_input("P", 1, len(doc), 1, key="pg", label_visibility="collapsed")

    with head_col4:
        focus_mode = st.toggle("Focus", value=True)

    with head_col5:
        analyze_btn = st.button("🔍 Analiz")

    st.divider()

    # --- OKUMA ALANI ---
    page = doc[page_num - 1]
    
    if analyze_btn:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0])) # Y ve X koordinatına göre sırala
        to_fr = GoogleTranslator(source='auto', target='fr')
        to_en = GoogleTranslator(source='auto', target='en')
        fr_html, en_html = "", ""

        with st.spinner("Analiz..."):
            for b in blocks:
                text = b[4].strip()
                if b[6] == 0 and len(text) > 2:
                    raw_fr = to_fr.translate(text)
                    raw_en = to_en.translate(text)
                    fr_html += f'<div class="para-block">{highlight_grammar(raw_fr, "fr")}</div>'
                    en_html += f'<div class="para-block">{highlight_grammar(raw_en, "en")}</div>'
        
        st.session_state.last_fr = fr_html
        st.session_state.last_en = en_html

    # Layout: Tablet yatayda (Landscape) mükemmel çalışır
    if focus_mode:
        col_fr, col_en = st.columns([1, 1])
        with col_fr:
            if 'last_fr' in st.session_state: st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
        with col_en:
            if 'last_en' in st.session_state: st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
    else:
        # Normal modda tableti yormamak için görsel kalitesini (zoom) dengeli tutuyoruz
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img = Image.open(io.BytesIO(pix.tobytes()))
        col_orig, col_trans = st.columns([1, 1])
        with col_orig:
            st.image(img, use_container_width=True)
        with col_trans:
            if 'last_fr' in st.session_state:
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div><div class="reading-box" style="border-top:3px solid #9b2c2c">{st.session_state.last_en}</div>', unsafe_allow_html=True)
else:
    st.info("Tabletten PDF yükleyerek başlayın.")