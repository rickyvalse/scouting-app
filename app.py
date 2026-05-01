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
# Assicurati che questo ID sia quello della cartella "MADRE" (quella condivisa)
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

def upload_to_drive(file_path, target_folder_id):
    """Carica un file specificando esattamente la cartella di destinazione."""
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [target_folder_id]
    }
    media = MediaFileUpload(
        file_path, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        resumable=True
    )
    
    try:
        # Controlla se il file esiste già NELLA SOTTOCARTELLA per aggiornarlo
        query = f"name = '{os.path.basename(file_path)}' and '{target_folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id)").execute().get('files', [])
        
        if results:
            drive_service.files().update(fileId=results[0]['id'], media_body=media).execute()
        else:
            drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    except Exception as e:
        st.error(f"Errore durante l'upload: {e}")

def get_or_create_player_folder(player_name):
    """Trova l'ID della cartella del giocatore. Se non esiste, la crea dentro FOLDER_ID."""
    player_slug = player_name.replace(" ", "_")
    query = f"name = '{player_slug}' and '{FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    
    try:
        results = drive_service.files().list(q=query, fields="files(id, name)").execute().get('files', [])
        if results:
            return results[0]['id']
        else:
            folder_metadata = {
                'name': player_slug,
                'parents': [FOLDER_ID],
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            return folder.get('id')
    except Exception as e:
        st.error(f"Errore creazione cartella: {e}")
        return None

def download_from_drive(folder_id, local_path):
    """Scarica tutto dal Drive all'avvio dell'app."""
    if not os.path.exists(local_path): os.makedirs(local_path)
    query = f"'{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute().get('files', [])
    for f in results:
        file_id = f['id']
        file_name = f['name']
        full_local_path = os.path.join(local_path, file_name)
        if f['mimeType'] == 'application/vnd.google-apps.folder':
            download_from_drive(file_id, full_local_path)
        else:
            request = drive_service.files().get_media(fileId=file_id)
            fh = io.FileIO(full_local_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

# --- INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="Tactical Scout Pro", layout="wide")

if 'data_loaded' not in st.session_state:
    if drive_service:
        with st.spinner("Sincronizzazione in corso..."):
            download_from_drive(FOLDER_ID, "data")
            st.session_state.data_loaded = True

BASE_DIR = "data"

# (CSS omesso per brevità, mantieni quello che hai già o usa questo base)
st.markdown("<style>.main-container { background: rgba(15, 18, 25, 0.9); padding: 20px; border-radius: 15px; color: white; }</style>", unsafe_allow_html=True)

if 'pagina' not in st.session_state: st.session_state.pagina = 'home'
if 'giocatore_sel' not in st.session_state: st.session_state.giocatore_sel = None

st.markdown('<div class="main-container">', unsafe_allow_html=True)

# 1. HOME
if st.session_state.pagina == 'home':
    st.title("🏟️ Scouting Archivio")
    c1, c2 = st.columns([3, 1])
    with c2:
        nuovo = st.popover("➕ Nuovo Atleta")
        n_atleta = nuovo.text_input("Nome Atleta")
        if nuovo.button("Conferma"):
            if n_atleta:
                # Crea cartella sia su Drive che in locale
                get_or_create_player_folder(n_atleta)
                os.makedirs(os.path.join(BASE_DIR, n_atleta.replace(" ", "_")), exist_ok=True)
                st.rerun()
    
    st.divider()
    if os.path.exists(BASE_DIR):
        giocatori = sorted([d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))])
        for g in giocatori:
            col_n, col_d = st.columns([6, 1])
            if col_n.button(f"👤 {g.replace('_', ' ')}", width='stretch'):
                st.session_state.giocatore_sel = g
                st.session_state.pagina = 'partite'
                st.rerun()
            if col_d.button("🗑️", key=f"del_{g}"):
                shutil.rmtree(os.path.join(BASE_DIR, g)); st.rerun()

# 2. PARTITE E VIDEO
elif st.session_state.pagina == 'partite':
    if st.button("⬅ Home"): st.session_state.pagina = 'home'; st.rerun()
    st.subheader(f"Scheda: {st.session_state.giocatore_sel.replace('_', ' ')}")
    
    t_d, t_v = st.tabs(["📊 Match Data", "🎞️ Video"])
    p_path = os.path.join(BASE_DIR, st.session_state.giocatore_sel)

    with t_d:
        if st.button("🚀 Inizia Scouting Live"):
            st.session_state.partita_attuale = datetime.now().strftime("%Y-%m-%d_%H-%M")
            st.session_state.dati_match = pd.DataFrame(columns=["Ora", "Azione", "Zona"])
            st.session_state.pagina = 'scouting'; st.rerun()
        
        if os.path.exists(p_path):
            for f in [f for f in os.listdir(p_path) if f.endswith('.xlsx')]:
                st.write(f"📄 {f}")

    with t_v:
        up = st.file_uploader("Carica Video", type=["mp4"])
        if up and st.button("Salva Video su Drive"):
            v_dir = os.path.join(p_path, "VIDEO")
            os.makedirs(v_dir, exist_ok=True)
            v_path = os.path.join(v_dir, up.name)
            with open(v_path, "wb") as f: f.write(up.getbuffer())
            # Carica nella sottocartella corretta
            id_cartella = get_or_create_player_folder(st.session_state.giocatore_sel)
            upload_to_drive(v_path, id_cartella)
            st.success("Video sincronizzato!"); st.rerun()

# 3. SCOUTING LIVE
elif st.session_state.pagina == 'scouting':
    st.title(f"Scouting: {st.session_state.giocatore_sel}")
    c_campo, c_act = st.columns([1, 1])
    
    with c_campo:
        for r in range(3):
            cs = st.columns(3)
            for c in range(3):
                nz = r*3+c+1
                if cs[c].button(f"Zona {nz}", width='stretch'): st.session_state.z_temp = f"Zona {nz}"
        st.dataframe(st.session_state.dati_match, width='stretch')

    with c_act:
        if 'z_temp' in st.session_state:
            st.markdown(f"📍 Selezionato: **{st.session_state.z_temp}**")
            for a in ["Pass ✅", "Tiro 🎯", "Recupero 🛡️", "Perso ⚠️"]:
                if st.button(a, width='stretch'):
                    nuova = pd.DataFrame([[datetime.now().strftime("%H:%M"), a, st.session_state.z_temp]], columns=["Ora", "Azione", "Zona"])
                    st.session_state.dati_match = pd.concat([st.session_state.dati_match, nuova], ignore_index=True)
        
        st.divider()
        if st.button("💾 SALVA E CHIUDI", type="primary", width='stretch'):
            # 1. Trova ID della sottocartella del giocatore
            id_sottocartella = get_or_create_player_folder(st.session_state.giocatore_sel)
            
            # 2. Crea file locale
            nome_file = f"Scout_{st.session_state.partita_attuale}.xlsx"
            path_locale = os.path.join(BASE_DIR, st.session_state.giocatore_sel, nome_file)
            st.session_state.dati_match.to_excel(path_locale, index=False)
            
            # 3. Carica ESATTAMENTE nell'ID della sottocartella
            upload_to_drive(path_locale, id_sottocartella)
            
            st.success("Dati inviati alla cartella corretta!")
            st.session_state.pagina = 'partite'
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
