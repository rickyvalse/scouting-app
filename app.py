import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil
import io

# --- CONFIGURAZIONE ---
BASE_DIR = "data"
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# --- UI & DESIGN (CONGELATO) ---
st.set_page_config(page_title="Tactical Scout Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Urbanist', sans-serif !important; color: #FFFFFF !important; }
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), 
                    url('https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .main-container {
        background: rgba(15, 18, 25, 0.95); padding: 30px; border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1); max-width: 1000px; margin: auto; backdrop-filter: blur(10px);
    }
    p, span, label, .stMarkdown, h1, h2, h3 { color: #FFFFFF !important; text-shadow: 1px 1px 2px rgba(0,0,0,0.8); }
    .stButton > button { background-color: #1b5e20 !important; color: white !important; border: none !important; font-weight: 600 !important; }
    .video-card { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGICA NAVIGAZIONE ---
if 'pagina' not in st.session_state: st.session_state.pagina = 'home'
if 'giocatore_sel' not in st.session_state: st.session_state.giocatore_sel = None

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# --- 1. HOME ---
if st.session_state.pagina == 'home':
    st.markdown("<h1>🏟️ Tactical Scout Pro</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        nuovo = st.popover("➕ Nuovo Atleta")
        n_atleta = nuovo.text_input("Inserisci Nome")
        if nuovo.button("Conferma"):
            if n_atleta:
                os.makedirs(os.path.join(BASE_DIR, n_atleta.replace(" ", "_")), exist_ok=True)
                st.rerun()
    st.divider()
    giocatori = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
    for g in giocatori:
        col_n, col_d = st.columns([7, 1])
        if col_n.button(f"👤 {g.replace('_', ' ')}", width='stretch', key=f"btn_{g}"):
            st.session_state.giocatore_sel = g
            st.session_state.pagina = 'partite'; st.rerun()
        if col_d.button("🗑️", key=f"del_{g}"):
            shutil.rmtree(os.path.join(BASE_DIR, g)); st.rerun()

# --- 2. SCHEDA GIOCATORE ---
elif st.session_state.pagina == 'partite':
    if st.button("⬅ Home"): st.session_state.pagina = 'home'; st.rerun()
    st.markdown(f"<h2>Analisi: {st.session_state.giocatore_sel.replace('_', ' ')}</h2>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📊 Sessioni", "🎞️ Videoteca"])
    p_path = os.path.join(BASE_DIR, st.session_state.giocatore_sel)

    with tab1:
        pop_match = st.popover("➕ Nuova Sessione", use_container_width=True)
        nome_m = pop_match.text_input("Titolo Match")
        if pop_match.button("Inizia Scouting"):
            st.session_state.partita_attuale = nome_m
            st.session_state.dati_match = pd.DataFrame(columns=["Ora", "Azione", "Zona"])
            st.session_state.pagina = 'scouting'; st.rerun()
        st.divider()
        if os.path.exists(p_path):
            files = sorted([x for x in os.listdir(p_path) if x.endswith('.xlsx')], reverse=True)
            for f in files:
                c_f, c_down, c_del = st.columns([5, 1, 1])
                c_f.write(f"📄 {f}")
                with open(os.path.join(p_path, f), "rb") as fd:
                    c_down.download_button("💾", fd, file_name=f, key=f"dl_{f}")
                if c_del.button("🗑️", key=f"del_f_{f}"):
                    os.remove(os.path.join(p_path, f)); st.rerun()

    with tab2:
        up = st.file_uploader("Carica Video MP4", type=["mp4"])
        if up:
            v_dir = os.path.join(p_path, "VIDEO")
            os.makedirs(v_dir, exist_ok=True)
            with open(os.path.join(v_dir, up.name), "wb") as f: f.write(up.getbuffer())
            st.success("Video Caricato!"); st.rerun()
        # Visualizzazione video (come prima)

# --- 3. SCOUTING LIVE (FIXED) ---
elif st.session_state.pagina == 'scouting':
    if st.button("⬅ Home (Annulla)"): st.session_state.pagina = 'home'; st.rerun()
    
    st.markdown(f"<h3>Match: {st.session_state.partita_attuale}</h3>", unsafe_allow_html=True)
    c_campo, c_act = st.columns([1, 1])
    
    with c_campo:
        for r in range(3):
            cs = st.columns(3)
            for c in range(3):
                nz = r*3+c+1
                if cs[c].button(f"Z{nz}", width='stretch', key=f"z{nz}"): 
                    st.session_state.z_temp = f"Zona {nz}"
        st.dataframe(st.session_state.dati_match, use_container_width=True, hide_index=True)
    
    with c_act:
        if 'z_temp' in st.session_state:
            st.info(f"Selezionato: {st.session_state.z_temp}")
            for a in ["Pass ✅", "Tiro 🎯", "Recupero 🛡️", "Perso ⚠️"]:
                if st.button(a, width='stretch'):
                    nuova_riga = pd.DataFrame([[datetime.now().strftime("%H:%M"), a, st.session_state.z_temp]], 
                                            columns=["Ora", "Azione", "Zona"])
                    st.session_state.dati_match = pd.concat([st.session_state.dati_match, nuova_riga], ignore_index=True)
        
        st.divider()
        
        # SALVATAGGIO LOCALE + DOWNLOAD
        if not st.session_state.dati_match.empty:
            # Creiamo il file Excel in memoria per il download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                st.session_state.dati_match.to_excel(writer, index=False)
            excel_data = output.getvalue()

            st.download_button(
                label="💾 SCARICA EXCEL E CHIUDI",
                data=excel_data,
                file_name=f"{st.session_state.partita_attuale}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                on_click=lambda: st.session_state.update({"pagina": "partite"})
            )
            st.caption("Nota: Il file verrà salvato sul tuo dispositivo.")

st.markdown('</div>', unsafe_allow_html=True)
