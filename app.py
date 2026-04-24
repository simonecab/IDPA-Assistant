import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader

# --- 1. CONFIGURAZIONE CLIENT (Nuova SDK 2026) ---
try:
    # Prende la chiave dai Secrets di Streamlit Cloud o dal file locale .toml
    client = genai.Client(api_key=st.secrets["api_key"])
except Exception as e:
    st.error("Errore: API Key non trovata. Controlla i Secrets su Streamlit Cloud.")
    st.stop()

# --- 2. FUNZIONE ESTRAZIONE TESTO PDF ---
@st.cache_data
def carica_conoscenza(lista_pdf):
    testo_totale = ""
    for nome_file in lista_pdf:
        try:
            reader = PdfReader(nome_file)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    # Pulizia per evitare errori di encoding con caratteri speciali
                    testo_totale += t.encode("utf-8", errors="ignore").decode("utf-8") + "\n"
        except Exception as e:
            st.warning(f"Attenzione: Impossibile leggere {nome_file}. Verifica che sia nella cartella principale.")
    return testo_totale

# --- 3. CONFIGURAZIONE DATI E PROMPT ---
nomi_files = [
    "2026 Eq Append-2.pdf",
    "2026 Match Admin-2.pdf",
    "2026-IDPA-Rulebook-2.pdf"
]

testo_regolamento = carica_conoscenza(nomi_files)

# Il tuo prompt specifico integrato con logica di ragionamento profondo
IL_TUO_PROMPT_BREVE = """
Ruolo: Sei l'assistente tecnico ufficiale di un Match Director IDPA. Il tuo compito è fornire interpretazioni regolamentari rapide, precise e imparziali.

Fonte di Verità: Utilizzerai esclusivamente i documenti caricati di seguito (Regolamento 2026 e suoi annex). Non fare affidamento su conoscenze esterne o regolamenti di altre federazioni (IPSC, USPSA, ecc.).

Protocollo di Risposta:
1. RAGIONAMENTO (THINKING HIGH): Controlla passo passo ogni regola e le diverse implicazioni, senza cercare scorciatoie. Analizza la situazione prima di rispondere.
2. Cita sempre la regola: Ogni risposta deve includere il numero del paragrafo o della sezione di riferimento (es. "Secondo la regola 4.15...").
3. Testo letterale: Se non è eccessivamente lungo riporta anche il testo letterale della regola.
4. Gerarchia dei documenti: In caso di conflitto fra regole, riporta chiaramente le regole in conflitto.
5. Onestà intellettuale: Se una situazione non è chiaramente coperta dai documenti caricati, rispondi: "Il regolamento non specifica questo caso particolare, si rimanda alla discrezione del Match Director". Non inventare soluzioni.
6. Non esitare a fare domande di chiarimento sulla situazione se possono esserci ambiguità nella situazione (ad esempio: di che caricatore si sta parlando? oppure il bersaglio è completamente ingaggiato? )
Tono: Professionale, asciutto e cortese.
"""

# Inversione gerarchica: Documenti seguiti dalle Istruzioni per massima attenzione del modello
SYSTEM_PROMPT = f"""
DOCUMENTAZIONE UFFICIALE IDPA 2026 CARICATA:
---
{testo_regolamento}
---

ISTRUZIONI OPERATIVE PER L'ASSISTENTE:
{IL_TUO_PROMPT_BREVE}

IMPORTANTE: Se un'azione non è esplicitamente vietata nel testo sopra, è da considerarsi legale. 
Prima di confermare una penalità (PE), cita la regola esatta che la impone.
"""

# --- 4. INTERFACCIA STREAMLIT ---
st.set_page_config(page_title="IDPA MD Assistant", page_icon="🎯")

# Titolo e Presentazione Documenti
st.title("🎯 IDPA MD Technical Assistant")
st.markdown(
    """
    <div style="font-size: 0.85em; color: #666; margin-bottom: 20px; line-height: 1.2;">
        MD Assistant basato su documenti ufficiali:<br>
        <i>• 2026 Eq Append-2.pdf &nbsp; • 2026 Match Admin-2.pdf &nbsp; • 2026-IDPA-Rulebook-2.pdf</i>
        by SimCab
    </div>
    """, 
    unsafe_allow_html=True
)

# Gestione della cronologia (Chat History)
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostra i messaggi precedenti
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Input Utente
if prompt := st.chat_input("Inserisci il quesito regolamentare..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generazione della risposta con il modello Pro 3.1
    with st.chat_message("assistant"):
        with st.spinner("Analisi High Thinking in corso..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-pro-preview",
                    contents=f"Analizza con estrema precisione tecnica: {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0,  # Precisione massima
                        top_p=0.95,
                        max_output_tokens=4096
                    )
                )
                
                risposta_testo = response.text
                st.markdown(risposta_testo)
                st.session_state.messages.append({"role": "assistant", "content": risposta_testo})
                
            except Exception as e:
                st.error(f"Errore durante l'analisi: {e}")

# Bottone laterale per pulire la sessione
if st.sidebar.button("Pulisci Conversazione"):
    st.session_state.messages = []
    st.rerun()
