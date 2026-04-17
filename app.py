import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import spacy
import os
import subprocess
import sys
from PIL import Image
import io

# --- MODELLERİ GARANTİYE ALAN YÜKLEME ---
@st.cache_resource
def load_nlp_models():
    models = {
        "fr": "fr_core_news_sm",
        "en": "en_core_web_sm"
    }
    loaded_models = {}
    for lang, model_name in models.items():
        try:
            # Önce yüklemeyi dene
            loaded_models[lang] = spacy.load(model_name)
        except:
            # Yüklü değilse indir ve sonra yükle
            subprocess.check_call([sys.executable, "-m", "spacy", "download", model_name])
            loaded_models[lang] = spacy.load(model_name)
    return loaded_models

# Modelleri çağır
nlp_models = load_nlp_models()

# --- RENKLENDİRME FONKSİYONU (GELİŞTİRİLMİŞ) ---
def highlight_grammar(text, lang_code):
    # Model yüklenemediyse ham metni döndür
    if lang_code not in nlp_models or nlp_models[lang_code] is None:
        return text
    
    try:
        doc = nlp_models[lang_code](text)
        html_output = ""
        for token in doc:
            # Renk paleti
            color = "#1a1a1a" # Varsayılan: Siyah/Koyu Gri
            
            # Kelime türüne göre renk ata
            if token.pos_ == "VERB":
                color = "#e67e22" # Turuncu: FİİLLER
            elif token.pos_ == "NOUN":
                color = "#2980b9" # Mavi: İSİMLER
            elif token.pos_ == "ADJ":
                color = "#27ae60" # Yeşil: SIFATLAR
            
            # HTML etiketini oluştur
            html_output += f'<span style="color:{color}; font-weight: 500;">{token.text}</span> '
        return html_output
    except:
        return text

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Reader AI", layout="wide", initial_sidebar_state="collapsed")

# --- TABLET VE TASARIM CSS ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 0.5rem !important; }
    .reading-box {
        background-color: #ffffff;
        padding: 30px;
        border-radius: 12px;
        border: 1px solid #e1e4e8;
        font-family: 'Georgia', serif;
        line-height: 1.8;
        font-size: 1.2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        color: #1a1a1a;
        margin-bottom: 20px;
    }
    .para-block { margin-bottom: 22px; display: block; }
    .lang-label {
        font-weight: bold; font-size: 0.8rem; color: #555;
        margin-bottom: 10px; display: block;
        letter-spacing: 1px; border-left: 3px solid #1f77b4; padding-left: 10px;
    }
    .stButton > button {
        height: 48px !important;
        background-color: #1f77b4 !important;
        color: white !important;
        font-size: 16px !important;
        border-radius: 10px !important;
    }
    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- ÜST PANEL ---
head_col1, head_col2, head_col3, head_col4, head_col5 = st.columns([1.5, 2, 0.7, 0.7, 1])

with head_col1:
    st.markdown("<h3 style='margin:0; color:#1f77b4;'>📖 Pro Reader AI</h3>", unsafe_allow_html=True)

with head_col2:
    uploaded_file = st.file_uploader("Yükle", type="pdf", label_visibility="collapsed")

if uploaded_file:
    if "last_file_id" not in st.session_state or st.session_state.last_file_id != uploaded_file.name:
        st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        st.session_state.last_file_id = uploaded_file.name
        st.session_state.pop('last_fr', None)
        st.session_state.pop('last_en', None)
        st.rerun()

    doc = st.session_state.pdf_doc

    with head_col3:
        page_num = st.number_input("P", 1, len(doc), 1, key="pg", label_visibility="collapsed")

    with head_col4:
        focus_mode = st.toggle("Focus", value=True)

    with head_col5:
        analyze_btn = st.button("🔍 Analiz Et")

    st.divider()

    # --- İŞLEME VE GÖRÜNTÜLEME ---
    page = doc[page_num - 1]
    
    if analyze_btn:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        to_fr = GoogleTranslator(source='auto', target='fr')
        to_en = GoogleTranslator(source='auto', target='en')
        
        fr_html, en_html = "", ""

        with st.spinner("Gramer analiz ediliyor..."):
            for b in blocks:
                text = b[4].strip()
                if b[6] == 0 and len(text) > 2:
                    raw_fr = to_fr.translate(text)
                    raw_en = to_en.translate(text)
                    
                    # Renklendirme burada çağrılıyor
                    fr_html += f'<div class="para-block">{highlight_grammar(raw_fr, "fr")}</div>'
                    en_html += f'<div class="para-block">{highlight_grammar(raw_en, "en")}</div>'
        
        st.session_state.last_fr = fr_html
        st.session_state.last_en = en_html

    # Layout Çıktısı
    if focus_mode:
        col_fr, col_en = st.columns([1, 1])
        with col_fr:
            st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA</span>', unsafe_allow_html=True)
            if 'last_fr' in st.session_state:
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
        with col_en:
            st.markdown('<span class="lang-label">🇬🇧 İNGİLİZCE</span>', unsafe_allow_html=True)
            if 'last_en' in st.session_state:
                st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
    else:
        col_orig, col_trans = st.columns([1, 1])
        with col_orig:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            st.image(Image.open(io.BytesIO(pix.tobytes())), use_container_width=True)
        with col_trans:
            if 'last_fr' in st.session_state:
                st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
                st.markdown('<span class="lang-label">🇬🇧 İNGİLİZCE</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
else:
    st.info("Üst panelden bir kitap yükleyerek başla.")
