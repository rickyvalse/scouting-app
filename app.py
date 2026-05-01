import streamlit as st
import pandas as pd
from datetime import datetime
import os
import shutil
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

# --- CONFIGURAZIONE GOOGLE DRIVE ---
FOLDER_ID = "1GZYzrzQHa9_LNjsbVbttmTbrFo9ha4AV"

def get_drive_service():
    try:
        info = st.secrets["gcp_service_account"]
        creds = service_account.Credentials.from_service_account_info(info)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Errore connessione Drive: {e}")
        return None

drive_service = get_drive_service()

# --- LOGICA DRIVE ---
def get_or_create_player_folder(player_name):
    player_slug = player_name.replace(" ", "_")
    query = f"name = '{player_slug}' and '{FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    try:
        results = drive_service.files().list(q=query, fields="files(id)").execute().get('files', [])
        if results: return results[0]['id']
        else:
            meta = {'name': player_slug, 'parents': [FOLDER_ID], 'mimeType': 'application/vnd.google-apps.folder'}
            folder = drive_service.files().create(body=meta, fields='id').execute()
            return folder.get('id')
    except: return None

def delete_from_drive(name, parent_id):
    try:
        query = f"name = '{name}' and '{parent_id}' in parents and trashed = false"
        res = drive_service.files().list(q=query, fields="files(id)").execute().get('files', [])
        if res:
            for f in res:
                drive_service.files().delete(fileId=f['id']).execute()
    except: pass

def upload_to_drive(file_path, target_id):
    file_metadata = {'name': os.path.basename(file_path), 'parents': [target_id]}
    media = MediaFileUpload(file_path, resumable=True)
    try:
        query = f"name = '{os.path.basename(file_path)}' and '{target_id}' in parents and trashed = false"
        res = drive_service.files().list(q=query).execute().get('files', [])
        if res: drive_service.files().update(fileId=res[0]['id'], media_body=media).execute()
        else: drive_service.files().create(body=file_metadata, media_body=media).execute()
    except: pass

def download_from_drive(folder_id, local_path):
    if not os.path.exists(local_path): os.makedirs(local_path)
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute().get('files', [])
        for f in results:
            full_path = os.path.join(local_path, f['name'])
            if f['mimeType'] == 'application/vnd.google-apps.folder': download_from_drive(f['id'], full_path)
            else:
                request = drive_service.files().get_media(fileId=f['id'])
                fh = io.FileIO(full_path, 'wb')
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done: _, done = downloader.next_chunk()
    except: pass

# --- UI & DESIGN ---
st.set_page_config(page_title="Tactical Scout Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] { 
        font-family: 'Urbanist', sans-serif !important; 
        color: #FFFFFF !important;
    }
    
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.8), rgba(0,0,0,0.8)), 
                    url('https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    
    .main-container {
        background: rgba(15, 18, 25, 0.95); padding: 30px; border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1); max-width: 1000px; margin: auto; backdrop-filter: blur(10px);
    }

    /* Leggibilità Scritte */
    p, span, label, .stMarkdown, h1, h2, h3 { 
        color: #FFFFFF !important; 
        text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
    }

    /* Tabs (Sessioni / Videoteca) */
    button[data-baseweb="tab"] p {
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: 700 !important;
    }

    /* --- FIX POPOVER (Pulsante statico) --- */
    div[data-testid="stPopover"] > button {
        background-color: transparent !important;
        border: 1px solid rgba(255,255,255,0.4) !important;
        color: white !important;
        box-shadow: none !important;
    }
    
    /* Rimuove effetto cambio colore al mouse */
    div[data-testid="stPopover"] > button:hover, 
    div[data-testid="stPopover"] > button:active,
    div[data-testid="stPopover"] > button:focus {
        background-color: transparent !important;
        border-color: rgba(255,255,255,0.4) !important;
        color: white !important;
    }

    /* Contenuto Popover */
    div[data-testid="stPopoverBody"] {
        background-color: #0f1219 !important;
        border: 1px solid #1b5e20 !important;
    }

    /* Input testo: Sfondo bianco per scrivere bene */
    div[data-testid="stPopoverBody"] input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 4px !important;
    }

    /* Pulsanti Standard */
    .stButton > button { 
        background-color: #1b5e20 !important; 
        color: white !important; 
        border: none !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background-color: #1b5e20 !important; /* Bloccato verde */
    }

    /* Video Box */
    .video-card {
        background: rgba(255,255,255,0.05);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP LOGIC ---
if 'data_loaded' not in st.session_state:
    with st.spinner("Sincronizzazione..."):
        download_from_drive(FOLDER_ID, "data")
        st.session_state.data_loaded = True

BASE_DIR = "data"
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
                get_or_create_player_folder(n_atleta)
                os.makedirs(os.path.join(BASE_DIR, n_atleta.replace(" ", "_")), exist_ok=True)
                st.rerun()
    
    st.divider()
    if os.path.exists(BASE_DIR):
        giocatori = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
        for g in giocatori:
            col_n, col_d = st.columns([7, 1])
            if col_n.button(f"👤 {g.replace('_', ' ')}", width='stretch'):
                st.session_state.giocatore_sel = g
                st.session_state.pagina = 'partite'
                st.rerun()
            if col_d.button("🗑️", key=f"del_{g}"):
                delete_from_drive(g, FOLDER_ID)
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
            files = [f for f in os.listdir(p_path) if f.endswith('.xlsx')]
            for f in sorted(files, reverse=True):
                c_f, c_down, c_del = st.columns([5, 1, 1])
                c_f.write(f"📄 {f}")
                with open(os.path.join(p_path, f), "rb") as fd:
                    c_down.download_button("💾", fd, file_name=f, key=f"dl_{f}")
                if c_del.button("🗑️", key=f"del_f_{f}"):
                    pid = get_or_create_player_folder(st.session_state.giocatore_sel)
                    delete_from_drive(f, pid)
                    os.remove(os.path.join(p_path, f)); st.rerun()

    with tab2:
        pop_video = st.popover("📤 Carica Video", use_container_width=True)
        up = pop_video.file_uploader("Seleziona MP4", type=["mp4"])
        if up and pop_video.button("Carica Ora"):
            v_dir = os.path.join(p_path, "VIDEO")
            os.makedirs(v_dir, exist_ok=True)
            v_path = os.path.join(v_dir, up.name)
            with open(v_path, "wb") as f: f.write(up.getbuffer())
            sid = get_or_create_player_folder(st.session_state.giocatore_sel)
            upload_to_drive(v_path, sid)
            st.rerun()

        st.divider()
        v_dir = os.path.join(p_path, "VIDEO")
        if os.path.exists(v_dir):
            video_files = [v for v in os.listdir(v_dir) if v.endswith('.mp4')]
            # Griglia a 3 colonne per video più piccoli
            cols = st.columns(3)
            for i, vn in enumerate(video_files):
                with cols[i % 3]:
                    st.markdown('<div class="video-card">', unsafe_allow_html=True)
                    st.write(f"🎥 {vn[:15]}...")
                    st.video(os.path.join(v_dir, vn))
                    if st.button("Elimina", key=f"v_del_{vn}"):
                        sid = get_or_create_player_folder(st.session_state.giocatore_sel)
                        delete_from_drive(vn, sid)
                        os.remove(os.path.join(v_dir, vn)); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

# --- 3. SCOUTING LIVE ---
elif st.session_state.pagina == 'scouting':
    st.markdown(f"<h3>Match: {st.session_state.partita_attuale}</h3>", unsafe_allow_html=True)
    c_campo, c_act = st.columns([1, 1])
    with c_campo:
        for r in range(3):
            cs = st.columns(3)
            for c in range(3):
                nz = r*3+c+1
                if cs[c].button(f"Z{nz}", width='stretch'): st.session_state.z_temp = f"Zona {nz}"
        st.dataframe(st.session_state.dati_match, use_container_width=True, hide_index=True)
    with c_act:
        if 'z_temp' in st.session_state:
            st.info(f"Punto: {st.session_state.z_temp}")
            for a in ["Pass ✅", "Tiro 🎯", "Recupero 🛡️", "Perso ⚠️"]:
                if st.button(a, width='stretch'):
                    nr = pd.DataFrame([[datetime.now().strftime("%H:%M"), a, st.session_state.z_temp]], columns=["Ora", "Azione", "Zona"])
                    st.session_state.dati_match = pd.concat([st.session_state.dati_match, nr], ignore_index=True)
        st.divider()
        if st.button("💾 SALVA E CHIUDI", width='stretch'):
            target_id = get_or_create_player_folder(st.session_state.giocatore_sel)
            nome_f = f"{st.session_state.partita_attuale}.xlsx"
            path_f = os.path.join(BASE_DIR, st.session_state.giocatore_sel, nome_f)
            st.session_state.dati_match.to_excel(path_f, index=False)
            upload_to_drive(path_f, target_id)
            st.session_state.pagina = 'partite'; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
