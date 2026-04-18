import streamlit as st
import fitz  # PyMuPDF
from deep_translator import GoogleTranslator
import spacy
import os
from PIL import Image
import io

# --- MODELLERİ OTOMATİK İNDİRME VE YÜKLEME ---
@st.cache_resource
def load_nlp_models():
    models = {
        "fr": "fr_core_news_sm",
        "en": "en_core_web_sm"
    }
    loaded_models = {}
    for lang, model_name in models.items():
        # Eğer model yüklü değilse indir
        if not spacy.util.is_package(model_name):
            try:
                os.system(f"python -m spacy download {model_name}")
            except Exception as e:
                st.error(f"Model yükleme hatası: {e}")
        
        # Modeli yükle
        try:
            loaded_models[lang] = spacy.load(model_name)
        except:
            st.warning(f"{lang.upper()} modeli yüklenemedi, renklendirme çalışmayabilir.")
            loaded_models[lang] = None
    return loaded_models

nlp_models = load_nlp_models()

# --- GRAMER RENKLENDİRME FONKSİYONU ---
def highlight_grammar(text, lang_code):
    if lang_code not in nlp_models or nlp_models[lang_code] is None:
        return text
    
    doc = nlp_models[lang_code](text)
    html_output = ""
    for token in doc:
        color = "#1a1a1a" # Varsayılan siyah
        if token.pos_ == "VERB": color = "#e67e22" # Turuncu - Fiil
        elif token.pos_ == "NOUN": color = "#2980b9" # Mavi - İsim
        elif token.pos_ == "ADJ": color = "#27ae60" # Yeşil - Sıfat
            
        html_output += f'<span style="color:{color};">{token.text}</span> '
    return html_output

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Pro Reader AI", layout="wide", initial_sidebar_state="collapsed")

# --- TABLET VE BEYAZ ŞERİT OPTİMİZASYONU (CSS) ---
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 0.5rem !important; }
    
    /* Okuma Kutusu Tasarımı */
    .reading-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #e0e4e8;
        font-family: 'Georgia', serif;
        line-height: 1.8;
        font-size: 1.15rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        color: #1a1a1a;
        margin-bottom: 15px;
    }
    
    .para-block { margin-bottom: 20px; display: block; }
    
    .lang-label {
        font-weight: bold; font-size: 0.75rem; color: #888;
        margin-bottom: 5px; display: block;
        letter-spacing: 1px;
    }

    /* Dokunmatik Dostu Butonlar */
    .stButton > button {
        height: 45px !important;
        background-color: #1f77b4 !important;
        color: white !important;
        font-weight: bold !important;
    }

    [data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- ÜST PANEL (HEADER) ---
head_col1, head_col2, head_col3, head_col4, head_col5 = st.columns([1.5, 2, 0.8, 0.8, 1])

with head_col1:
    st.markdown("<h3 style='margin:0; color:#1f77b4;'>📖 Pro Reader</h3>", unsafe_allow_html=True)

with head_col2:
    uploaded_file = st.file_uploader("Dosya Seç", type="pdf", label_visibility="collapsed")

# --- DOSYA VE SESSION KONTROLÜ ---
if uploaded_file:
    # Yeni dosya yüklendiğinde temizlik yap
    if "last_file_id" not in st.session_state or st.session_state.last_file_id != uploaded_file.name:
        st.session_state.pdf_doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        st.session_state.last_file_id = uploaded_file.name
        if 'last_fr' in st.session_state: del st.session_state.last_fr
        if 'last_en' in st.session_state: del st.session_state.last_en
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
        # PDF bloklarını dikey koordinata göre analiz et (Mizanpajı korur)
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        to_fr = GoogleTranslator(source='auto', target='fr')
        to_en = GoogleTranslator(source='auto', target='en')
        
        fr_html, en_html = "", ""

        with st.spinner("Metinler analiz ediliyor..."):
            for b in blocks:
                text = b[4].strip()
                if b[6] == 0 and len(text) > 2:
                    try:
                        raw_fr = to_fr.translate(text)
                        raw_en = to_en.translate(text)
                        
                        colored_fr = highlight_grammar(raw_fr, "fr")
                        colored_en = highlight_grammar(raw_en, "en")
                        
                        fr_html += f'<div class="para-block">{colored_fr}</div>'
                        en_html += f'<div class="para-block">{colored_en}</div>'
                    except:
                        continue
        
        st.session_state.last_fr = fr_html
        st.session_state.last_en = en_html

    # --- EKRAN DÜZENİ ---
    if focus_mode:
        # Odaklanma Modu: Sadece FR ve EN yan yana
        col_fr, col_en = st.columns([1, 1])
        with col_fr:
            st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA (HEDEF)</span>', unsafe_allow_html=True)
            if 'last_fr' in st.session_state:
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
        with col_en:
            st.markdown('<span class="lang-label">🇬🇧 İNGİLİZCE (DESTEK)</span>', unsafe_allow_html=True)
            if 'last_en' in st.session_state:
                st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
    else:
        # Normal Mod: Orijinal Sayfa | Çeviriler (Alt Alta)
        col_orig, col_trans = st.columns([1, 1])
        with col_orig:
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img = Image.open(io.BytesIO(pix.tobytes()))
            st.image(img, use_container_width=True)
        with col_trans:
            if 'last_fr' in st.session_state:
                st.markdown('<span class="lang-label">🇫🇷 FRANSIZCA</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="reading-box">{st.session_state.last_fr}</div>', unsafe_allow_html=True)
                st.markdown('<span class="lang-label">🇬🇧 İNGİLİZCE</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="reading-box">{st.session_state.last_en}</div>', unsafe_allow_html=True)
else:
    st.info("Lütfen yukarıdaki panelden bir PDF yükleyerek başlayın kral.")
