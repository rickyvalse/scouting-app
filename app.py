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
        st.error(f"Errore di connessione a Google Drive: {e}")
        return None

drive_service = get_drive_service()

# --- FUNZIONI SINCRONIZZAZIONE ---
def upload_to_drive(file_path, folder_id):
    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    # Aggiungiamo mimetype per aiutare Google a capire che è un file Excel o Video
    media = MediaFileUpload(file_path, resumable=True)
    
    query = f"name = '{os.path.basename(file_path)}' and '{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query).execute().get('files', [])
    
    try:
        if results:
            # Se esiste già, lo aggiorna
            drive_service.files().update(fileId=results[0]['id'], media_body=media).execute()
        else:
            # Se non esiste, lo crea
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    except Exception as e:
        st.error(f"Errore durante l'upload su Drive: {e}")

def download_from_drive(folder_id, local_path):
    if not os.path.exists(local_path): os.makedirs(local_path)
    query = f"'{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query).execute().get('files', [])
    for f in results:
        file_id = f['id']
        file_name = f['name']
        file_mime = f.get('mimeType', '')
        full_local_path = os.path.join(local_path, file_name)
        if file_mime == 'application/vnd.google-apps.folder':
            download_from_drive(file_id, full_local_path)
        else:
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(full_local_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tactical Scout Pro", layout="wide")

if 'data_loaded' not in st.session_state:
    if drive_service:
        with st.spinner("Sincronizzazione dati con Google Drive..."):
            download_from_drive(FOLDER_ID, "data")
            st.session_state.data_loaded = True

BASE_DIR = "data"

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Urbanist', sans-serif !important; }
    .stApp {
        background: linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)), 
                    url('https://images.unsplash.com/photo-1556056504-5c7696c4c28d?q=80&w=2076&auto=format&fit=crop');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .main-container {
        background: rgba(15, 18, 25, 0.92); padding: 25px 35px; border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.1); max-width: 850px; margin: auto; backdrop-filter: blur(10px);
    }
    h1 { font-size: 38px !important; font-weight: 700 !important; color: white !important; text-align: center; }
    .stButton > button { background-color: rgba(46, 125, 50, 0.9) !important; color: white !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'pagina' not in st.session_state: st.session_state.pagina = 'home'
if 'giocatore_sel' not in st.session_state: st.session_state.giocatore_sel = None

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 1. HOME
if st.session_state.pagina == 'home':
    st.markdown("<h1>🏟️ Archivio Scouting Pro</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c2:
        nuovo = st.popover("➕ Nuovo Atleta")
        n_atleta = nuovo.text_input("Nome")
        if nuovo.button("Crea"):
            if n_atleta:
                atleta_slug = n_atleta.replace(" ", "_")
                os.makedirs(os.path.join(BASE_DIR, atleta_slug), exist_ok=True)
                meta = {'name': atleta_slug, 'parents': [FOLDER_ID], 'mimeType': 'application/vnd.google-apps.folder'}
                drive_service.files().create(body=meta).execute()
                st.rerun()
    
    st.divider()
    if os.path.exists(BASE_DIR):
        giocatori = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
        for g in giocatori:
            col_n, col_d = st.columns([6, 1])
            # AGGIORNATO: width='stretch'
            if col_n.button(f"👤 {g.replace('_', ' ')}", width='stretch'):
                st.session_state.giocatore_sel = g
                st.session_state.pagina = 'partite'
                st.rerun()
            if col_d.button("🗑️", key=f"del_{g}"):
                shutil.rmtree(os.path.join(BASE_DIR, g)); st.rerun()

# 2. SESSIONI E VIDEO
elif st.session_state.pagina == 'partite':
    if st.button("⬅ Torna alla Home"):
        st.session_state.pagina = 'home'; st.rerun()
    
    st.markdown(f"<h2>👤 {st.session_state.giocatore_sel.replace('_', ' ')}</h2>", unsafe_allow_html=True)
    t_d, t_v = st.tabs(["📊 Match", "🎞️ Video"])
    
    p_path = os.path.join(BASE_DIR, st.session_state.giocatore_sel)
    
    with t_d:
        if st.button("➕ Nuova Partita"):
            st.session_state.partita_attuale = datetime.now().strftime("%d-%m_%H-%M")
            st.session_state.dati_match = pd.DataFrame(columns=["Ora", "Azione", "Zona"])
            st.session_state.pagina = 'scouting'; st.rerun()
        
        if os.path.exists(p_path):
            files = [f for f in os.listdir(p_path) if f.endswith('.xlsx')]
            for f in files:
                st.write(f"📄 {f}")
                with open(os.path.join(p_path, f), "rb") as ex:
                    st.download_button("Scarica Excel", ex, file_name=f, key=f"dl_{f}")

    with t_v:
        up = st.file_uploader("Carica Video", type=["mp4","mov"])
        if up and st.button("🚀 Salva permanentemente"):
            v_dir = os.path.join(p_path, "VIDEO")
            os.makedirs(v_dir, exist_ok=True)
            v_full_path = os.path.join(v_dir, up.name)
            with open(v_full_path, "wb") as f: f.write(up.getbuffer())
            q = f"name = '{st.session_state.giocatore_sel}' and '{FOLDER_ID}' in parents"
            res = drive_service.files().list(q=q).execute().get('files', [])
            if res: upload_to_drive(v_full_path, res[0]['id'])
            st.success("Video caricato su Drive!"); st.rerun()
        
        v_dir = os.path.join(p_path, "VIDEO")
        if os.path.exists(v_dir):
            for vn in os.listdir(v_dir):
                st.video(os.path.join(v_dir, vn))

# 3. SCOUTING LIVE
elif st.session_state.pagina == 'scouting':
    st.markdown(f"<h1>⚽ Match: {st.session_state.partita_attuale}</h1>", unsafe_allow_html=True)
    c_campo, c_act = st.columns([1, 1])
    with c_campo:
        for r in range(3):
            cs = st.columns(3)
            for c in range(3):
                nz = r*3+c+1
                # AGGIORNATO: width='stretch'
                if cs[c].button(f"Z{nz}", width='stretch'): 
                    st.session_state.z_temp = f"Zona {nz}"
        # AGGIORNATO: width='stretch'
        st.dataframe(st.session_state.dati_match, width='stretch')
    with c_act:
        if 'z_temp' in st.session_state:
            st.markdown(f"### 📍 {st.session_state.z_temp}")
            for a in ["Pass ✅", "Tiro 🎯", "Recupero 🛡️", "Perso ⚠️"]:
                # AGGIORNATO: width='stretch'
                if st.button(a, width='stretch'):
                    nuova_riga = pd.DataFrame([[datetime.now().strftime("%H:%M"), a, st.session_state.z_temp]], columns=["Ora", "Azione", "Zona"])
                    st.session_state.dati_match = pd.concat([st.session_state.dati_match, nuova_riga], ignore_index=True)
        # AGGIORNATO: width='stretch'
        if st.button("💾 SALVA E SINCRONIZZA", type="primary", width='stretch'):
            fname = f"Scout_{st.session_state.partita_attuale}.xlsx"
            local_fpath = os.path.join(BASE_DIR, st.session_state.giocatore_sel, fname)
            st.session_state.dati_match.to_excel(local_fpath, index=False)
            q = f"name = '{st.session_state.giocatore_sel}' and '{FOLDER_ID}' in parents"
            res = drive_service.files().list(q=q).execute().get('files', [])
            if res: upload_to_drive(local_fpath, res[0]['id'])
            st.session_state.pagina = 'partite'; st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
