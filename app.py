import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil

# Configurazione Pagina
st.set_page_config(page_title="Tactical Scout Pro", layout="wide")

# --- CSS PROFESSIONALE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Urbanist', sans-serif !important;
    }

    /* Sfondo */
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)),
                    url('https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Contenitore Centrale */
    .main-container {
        background: rgba(15, 18, 25, 0.92);
        padding: 25px 35px;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1);
        max-width: 850px;
        margin: auto;
        backdrop-filter: blur(10px);
    }

    /* TITOLI E SOTTOTITOLI GRANDI */
    h1 {
        font-size: 38px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        text-align: center;
        margin-bottom: 20px !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    h2 {
        font-size: 30px !important;
        font-weight: 700 !important;
        color: #ffffff !important;
        margin-top: 10px !important;
    }
    h3 {
        font-size: 24px !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }

    /* Nome Video Sopra la Clip */
    .video-label {
        font-size: 14px;
        font-weight: 600;
        color: #00ff00;
        margin-bottom: 5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Bottoni */
    .stButton > button {
        background-color: rgba(46, 125, 50, 0.9) !important;
        color: white !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
    }

    .btn-back > div [data-testid="stButton"] button {
        background-color: transparent !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        color: #ffffff !important;
    }

    div[key*="del"] button, div[key*="rm"] button {
        background-color: #b71c1c !important;
    }

    /* Spaziature */
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA ---
BASE_DIR = "data"
if not os.path.exists(BASE_DIR): os.makedirs(BASE_DIR)

if 'pagina' not in st.session_state: st.session_state.pagina = 'home'
if 'giocatore_sel' not in st.session_state: st.session_state.giocatore_sel = None

# --- UI ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 1. HOME
if st.session_state.pagina == 'home':
    st.markdown("<h1>🏟️ Archivio Scouting Pro</h1>", unsafe_allow_html=True)

    col_h1, col_h2 = st.columns([3, 1])
    with col_h2:
        nuovo = st.popover("➕ Nuovo")
        nome_n = nuovo.text_input("Nome Atleta")
        if nuovo.button("Crea Scheda"):
            if nome_n:
                os.makedirs(os.path.join(BASE_DIR, nome_n.replace(" ", "_")), exist_ok=True)
                st.rerun()

    st.divider()

    giocatori = sorted(os.listdir(BASE_DIR))
    for g in giocatori:
        c_n, c_d = st.columns([6, 1])
        if c_n.button(f"👤 {g.replace('_', ' ')}", use_container_width=True, key=f"go_{g}"):
            st.session_state.giocatore_sel = g
            st.session_state.pagina = 'partite'
            st.rerun()
        if c_d.button("🗑️", key=f"del_{g}", use_container_width=True):
            shutil.rmtree(os.path.join(BASE_DIR, g))
            st.rerun()

# 2. DETTAGLIO GIOCATORE
elif st.session_state.pagina == 'partite':
    col_back, _ = st.columns([1, 4])
    with col_back:
        st.markdown('<div class="btn-back">', unsafe_allow_html=True)
        if st.button("⬅ Home"):
            st.session_state.pagina = 'home'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"<h2>👤 {st.session_state.giocatore_sel.replace('_', ' ')}</h2>", unsafe_allow_html=True)

    st.divider()

    tab_d, tab_v = st.tabs(["📊 Sessioni Dati", "🎞️ Video Clip"])

    with tab_d:
        st.markdown("<h3>📂 Partite Salvate</h3>", unsafe_allow_html=True)
        col_m1, col_m2 = st.columns([3, 1.2])
        with col_m2:
            n_p = st.popover("➕ Nuova Partita")
            m_name = n_p.text_input("Nome Match")
            if n_p.button("Avvia Scouting"):
                st.session_state.partita_attuale = m_name
                st.session_state.dati_match = pd.DataFrame(columns=["Ora", "Azione", "Zona"])
                st.session_state.pagina = 'scouting'; st.rerun()

        path_p = os.path.join(BASE_DIR, st.session_state.giocatore_sel)
        files = sorted([f for f in os.listdir(path_p) if f.endswith('.xlsx')])
        for f in files:
            cf1, cf2, cf3 = st.columns([4, 1, 1])
            cf1.write(f"📄 {f}")
            with open(os.path.join(path_p, f), "rb") as ex:
                cf2.download_button("📥", ex, file_name=f, key=f"dl_{f}")
            if cf3.button("🗑️", key=f"rm_{f}"):
                os.remove(os.path.join(path_p, f)); st.rerun()

    with tab_v:
        st.markdown("<h3>🎥 Videoteca</h3>", unsafe_allow_html=True)
        up = st.file_uploader("Carica Clip", type=["mp4","mov"], accept_multiple_files=True)
        if up and st.button("💾 Salva in Archivio"):
            v_path = os.path.join(BASE_DIR, st.session_state.giocatore_sel, "VIDEO_CLIPS")
            os.makedirs(v_path, exist_ok=True)
            for v in up:
                with open(os.path.join(v_path, v.name), "wb") as fv: fv.write(v.getbuffer())
            st.rerun()

        st.divider()
        v_path = os.path.join(BASE_DIR, st.session_state.giocatore_sel, "VIDEO_CLIPS")
        if os.path.exists(v_path):
            v_cols = st.columns(3)
            for i, vn in enumerate(sorted(os.listdir(v_path))):
                with v_cols[i%3]:
                    # NOME DEL VIDEO SOPRA LA CLIP
                    st.markdown(f'<p class="video-label">🎬 {vn}</p>', unsafe_allow_html=True)
                    st.video(os.path.join(v_path, vn))
                    if st.button("Elimina", key=f"dv_{vn}", use_container_width=True):
                        os.remove(os.path.join(v_path, vn)); st.rerun()

# 3. SCOUTING LIVE
elif st.session_state.pagina == 'scouting':
    st.markdown(f"<h1>⚽ Match: {st.session_state.part_attuale}</h1>", unsafe_allow_html=True)
    c_campo, c_azioni = st.columns([1, 1])
    with c_campo:
        for r in range(3):
            cs = st.columns(3)
            for c in range(3):
                nz = r*3+c+1
                if cs[c].button(f"Z{nz}", use_container_width=True):
                    st.session_state.z_temp = f"Zona {nz}"
        st.dataframe(st.session_state.dati_match, use_container_width=True)

    with c_azioni:
        if 'z_temp' in st.session_state:
            st.markdown(f"<h3>📍 {st.session_state.z_temp}</h3>", unsafe_allow_html=True)
            for a in ["Passaggio ✅", "Tiro 🎯", "Recupero 🛡️", "Perso ⚠️"]:
                if st.button(a, use_container_width=True):
                    n_r = pd.DataFrame([[datetime.now().strftime("%H:%M"), a, st.session_state.z_temp]], columns=["Ora", "Azione", "Zona"])
                    st.session_state.dati_match = pd.concat([st.session_state.dati_match, n_r], ignore_index=True)

        if st.button("💾 SALVA SESSIONE", type="primary", use_container_width=True):
            f_name = f"Match_{st.session_state.partita_attuale}.xlsx"
            st.session_state.dati_match.to_excel(os.path.join(BASE_DIR, st.session_state.giocatore_sel, f_name), index=False)
            st.session_state.pagina = 'partite'; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
