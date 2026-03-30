import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader

# 1. Recupero della chiave dal file secrets.toml
try:
    genai.configure(api_key=st.secrets["api_key"])
except Exception as e:
    st.error("Errore: API Key non trovata nel file .streamlit/secrets.toml")
    st.stop()

# 2. Funzione per estrarre il testo dai tuoi 3 PDF



@st.cache_data
def carica_conoscenza(lista_pdf):
    testo_estratto = ""
    for nome_file in lista_pdf:
        try:
            reader = PdfReader(nome_file)
            for page in reader.pages:
                # Estraiamo il testo
                t = page.extract_text()
                if t:
                    # Forziamo la codifica in utf-8 ignorando i caratteri "sporchi"
                    testo_estratto += t.encode("utf-8", errors="ignore").decode("utf-8") + "\n"
        except Exception as e:
            st.warning(f"Impossibile leggere il file {nome_file}: {e}")
    return testo_estratto








# --- MODIFICA QUESTE RIGHE ---
nomi_files = ["2026-IDPA-Rulebook-2.pdf", "2026 Match Admin-2.pdf", "2026 Eq Append-2.pdf"] 
IL_TUO_PROMPT_BREVE = """
Ruolo: Sei l'assistente tecnico ufficiale del Match Director IDPA. Il tuo compito   fornire interpretazioni regolamentari rapide, precise e imparziali.

Fonte di Verit : Utilizzerai esclusivamente i documenti  caricati doi seguito (Regolamento 2026 e suoi annex). Non fare affidamento su conoscenze esterne o regolamenti di altre federazioni (IPSC, USPSA, ecc.).

Protocollo di Risposta:

    Cita sempre la regola: Ogni risposta deve includere il numero del paragrafo o della sezione di riferimento (es. "Secondo la regola 4.15...").
Se non   eccessivamente lungo riporta anche il testo letterale della regola.

    Gerarchia dei documenti: In caso di conflitto fra regole, riporta chiaramente le regole in conflitto.

    Onest  intellettuale: Se una situazione non   chiaramente coperta dai documenti caricati, rispondi: "Il regolamento non specifica questo caso particolare, si rimanda alla discrezione del Match Director". Non inventare soluzioni.

    Tono: Professionale, asciutto e cortese.
    """
# -----------------------------

# Estrazione del contenuto dei PDF
corpo_conoscenza = carica_conoscenza(nomi_files)

# Costruzione del System Prompt finale (Testo + PDF)
SYSTEM_PROMPT = f"""
{IL_TUO_PROMPT_BREVE}

DI SEGUITO I DOCUMENTI UFFICIALI DI RIFERIMENTO (40 PAGINE):
---
{corpo_conoscenza}
---
Usa esclusivamente queste informazioni per rispondere. Se le regole sono interconnesse, analizzale tutte prima di rispondere.
"""

# 3. Inizializzazione del Modello Gemini
# Impostiamo la temperatura a 0 e il modello corretto
model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=SYSTEM_PROMPT,
    generation_config={
        "temperature": 0,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }
)

# 4. Interfaccia Streamlit
st.set_page_config(page_title="IDPA MD Assistant", layout="centered")
st.title("IDPA MD Assistant - Rulebook 2026")

# Gestione della cronologia della chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra i messaggi precedenti
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input dell'utente
if prompt := st.chat_input("Fai una domanda sulle regole..."):
    # Aggiungi messaggio utente alla cronologia
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Risposta dell'AI
    with st.chat_message("assistant"):
        with st.spinner("Consultando le 40 pagine di regole..."):
            # Avviamo la chat passando la cronologia precedente
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages[:-1]
            ])
            
            try:
                response = chat.send_message(prompt)
                full_response = response.text
                st.markdown(full_response)
                # Salviamo la risposta dell'assistente
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Si   verificato un errore nella generazione: {e}")