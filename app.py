import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader

# --- 1. CONFIGURAZIONE CLIENT ---
client = genai.Client(api_key=st.secrets["api_key"])

# --- 2. CARICAMENTO PDF ---
@st.cache_data
def carica_conoscenza(lista_pdf):
    testo_totale = ""
    for nome_file in lista_pdf:
        try:
            reader = PdfReader(nome_file)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    testo_totale += t.encode("utf-8", errors="ignore").decode("utf-8") + "\n"
        except Exception as e:
            st.error(f"Errore nel file {nome_file}: {e}")
    return testo_totale

nomi_files = ["2026 Eq Append-2.pdf", "2026 Match Admin-2.pdf", "2026-IDPA-Rulebook-2.pdf"]
testo_regolamento = carica_conoscenza(nomi_files)

# --- 3. PROMPT STRUTTURATO (IL SEGRETO) ---
# Spostiamo il tuo prompt DOPO il testo per dargli massima importanza
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

# Configurazione del System Instruction con gerarchia invertita
SYSTEM_PROMPT = f"""
I SEGUENTI SONO I DOCUMENTI UFFICIALI IDPA 2026:
---
{testo_regolamento}
---

ORA APPLICA QUESTE ISTRUZIONI AI DOCUMENTI SOPRA:
{IL_TUO_PROMPT_BREVE}
"""

# --- 4. INTERFACCIA ---
st.set_page_config(page_title="IDPA AI Assistant", layout="centered")
st.title("🎯 IDPA Technical Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

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
                # Usiamo il modello Pro 3.1 che è quello che ti ha convinto
                response = client.models.generate_content(
                    model="gemini-3.1-pro-preview",
                    contents=f"ANALIZZA CON ATTENZIONE (THINK HIGH): {prompt}",
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0, # Cruciale per evitare allucinazioni
                        top_p=0.95,
                        max_output_tokens=4096
                    )
                )
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
            except Exception as e:
                st.error(f"Errore: {e}")
