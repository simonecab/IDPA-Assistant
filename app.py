import streamlit as st
import hashlib
import datetime
from google import genai
from google.genai import types
from streamlit_cookies_controller import CookieController

# --- 0. IMPOSTAZIONI PAGINA E AUTENTICAZIONE ---
st.set_page_config(page_title="IDPA AI Assistant", layout="centered")

controller = CookieController()

# 1. Gestione Logout in sospeso (eseguita PRIMA di leggere eventuali cookie)
if st.session_state.get("logout_richiesto"):
    controller.remove("ruolo_utente", path="/")
    st.session_state.ruolo_utente = None
    del st.session_state["logout_richiesto"]
    cookie_ruolo = None # Forza l'ignoramento del cookie in questo ciclo
else:
    cookie_ruolo = controller.get("ruolo_utente")

# 2. Inizializzazione e lettura sicura del cookie
# (Risolve la latenza di caricamento asincrono del componente web)
if cookie_ruolo and st.session_state.get("ruolo_utente") != cookie_ruolo:
    st.session_state.ruolo_utente = cookie_ruolo
elif "ruolo_utente" not in st.session_state:
    st.session_state.ruolo_utente = None

# Sicurezza: Carica il Master PIN dai segreti
try:
    MASTER_PIN = str(st.secrets["master_pin"])
except KeyError:
    st.error("⚠️ Errore: Manca 'master_pin' nel file secrets.toml")
    st.stop()

# Funzioni matematiche e date
def genera_pin_giornaliero(data_target, master_pin):
    stringa_base = f"{data_target.isoformat()}-{master_pin}"
    hash_object = hashlib.sha256(stringa_base.encode())
    numero_hash = int(hash_object.hexdigest(), 16)
    return f"{numero_hash % 1000:03d}"

def formatta_data(data):
    mesi =["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    return f"{data.day:02d}/{mesi[data.month - 1]}"

oggi = datetime.date.today()
domani = oggi + datetime.timedelta(days=1)
dopodomani = oggi + datetime.timedelta(days=2)

pin_oggi = genera_pin_giornaliero(oggi, MASTER_PIN)
pin_domani = genera_pin_giornaliero(domani, MASTER_PIN)
pin_dopodomani = genera_pin_giornaliero(dopodomani, MASTER_PIN)

# --- SCHERMATA DI LOGIN ---
if st.session_state.ruolo_utente is None:
    login_container = st.empty()
    with login_container.container():
        st.title("🎯 IDPA Technical Assistant")
        
        st.markdown("""
        **MD Assistant basato su documenti ufficiali:**  
        • 2026 Eq Append-2.pdf  
        • 2026 Match Admin-2.pdf  
        • 2026-IDPA-Rulebook-2.pdf  

        Sviluppata da **simcab** ([cabasino@gmail.com](mailto:cabasino@gmail.com))
        """)
        st.divider()
        st.info("Per il pin del giorno rivolgersi a Simone Cab: cabasino@gmail.com")
        
        pin_inserito = st.text_input("Inserisci il PIN (Master o Giornaliero):", type="password")
        
        if st.button("Accedi"):
            if pin_inserito == MASTER_PIN:
                st.session_state.ruolo_utente = "master"
                st.session_state.scrivi_cookie = "master" # Flag per la scrittura ritardata
                login_container.empty()
            elif pin_inserito == pin_oggi:
                st.session_state.ruolo_utente = "giornaliero"
                st.session_state.scrivi_cookie = "giornaliero"
                login_container.empty()
            else:
                st.error("PIN errato o scaduto. Riprova.")
                st.stop()
        else:
            st.stop() # Ferma il rendering qui finché non si accede

# ==============================================================
# DA QUI IN POI IL CODICE GIRA SOLO SE L'UTENTE E' AUTORIZZATO
# ==============================================================

# 3. Esecuzione del comando Javascript per il cookie nel blocco principale
# (Garantisce che il DOM sopravviva e scriva fisicamente il dato nel browser)
if st.session_state.get("scrivi_cookie"):
    if st.session_state.scrivi_cookie == "master":
        controller.set("ruolo_utente", "master", max_age=2592000, path="/")
    else:
        controller.set("ruolo_utente", "giornaliero", max_age=43200, path="/")
    del st.session_state["scrivi_cookie"]

# --- CONFIGURAZIONE CLIENT E CONOSCENZA ---
try:
    client = genai.Client(api_key=st.secrets["api_key"])
except KeyError:
    st.error("⚠️ Errore: Manca 'api_key' nel file secrets.toml")
    st.stop()

@st.cache_data
def carica_conoscenza(nome_file_txt):
    try:
        with open(nome_file_txt, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        st.error(f"Errore di lettura: {e}")
        st.stop()

testo_regolamento = carica_conoscenza("regolamento_completo.txt")

# --- PROMPT STRUTTURATO ---
IL_TUO_PROMPT_BREVE = """
RUOLO: Sei l'assistente tecnico ufficiale del Match Director IDPA. Fornisci interpretazioni rapide, precise e imparziali.
FONTE DI VERITÀ: Usa SOLO i documenti sopra. Non usare conoscenze esterne.

PROTOCOLLO DECISIONALE (THINKING HIGH):
1. Prima di rispondere, scrivi una sezione 'ANALISI LOGICA' dove verifichi se l'azione descritta viola esplicitamente una regola.
2. Se non esiste una regola che lo vieti, l'azione è LEGALE. Non dedurre penalità per analogia.
3. Cita sempre il numero del paragrafo e riporta il testo letterale se rilevante.
4. Se il caso non è coperto, rimanda alla discrezione del Match Director.
5. Tono: Professionale, asciutto e cortese.
"""

SYSTEM_PROMPT = f"""
I SEGUENTI SONO I DOCUMENTI UFFICIALI IDPA 2026:
---
{testo_regolamento}
---

ORA APPLICA QUESTE ISTRUZIONI AI DOCUMENTI SOPRA:
{IL_TUO_PROMPT_BREVE}
"""

# --- INTERFACCIA APP SBLOCCATA ---
st.title("🎯 IDPA Technical Assistant")

st.markdown("""
**MD Assistant basato su documenti ufficiali:**  
• 2026 Eq Append-2.pdf  
• 2026 Match Admin-2.pdf  
• 2026-IDPA-Rulebook-2.pdf  

Sviluppata da **simcab** ([cabasino@gmail.com](mailto:cabasino@gmail.com))
""")

if st.session_state.ruolo_utente == "master":
    st.markdown(f"🔑 **PIN:** {formatta_data(oggi)}: **{pin_oggi}** | {formatta_data(domani)}: **{pin_domani}** | {formatta_data(dopodomani)}: **{pin_dopodomani}**")

st.divider()

# --- LOGICA DELLA CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = list()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("Descrivi la situazione..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Ragionamento profondo in corso..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-pro-preview",
                    contents=f"ANALIZZA CON ATTENZIONE (THINK HIGH): {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0,
                        top_p=0.95,
                        max_output_tokens=4096
                    )
                )
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Errore: {e}")

# --- LOGOUT ---
st.divider()
if st.button("Chiudi Sessione"):
    st.session_state.logout_richiesto = True
    st.session_state.messages = list()
    st.rerun()