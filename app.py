import streamlit as st
import pandas as pd
import openai
import json

st.set_page_config(page_title="Magic Commander Builder", layout="wide")

st.title("🧙‍♂️ Magic Commander Deck Builder")
st.write("Lade deine angereicherte Sammlung hoch, um deinen Commander zu wählen.")

uploaded_file = st.file_uploader("master_collection.csv hochladen", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    commanders = df[df['Is Legendary'] == True]
    
    st.subheader("1. Wähle deinen Commander")
    commander_name = st.selectbox("Commander auswählen:", commanders['Name'].sort_values())
    
    if commander_name:
        cmd_data = commanders[commanders['Name'] == commander_name].iloc[0]
        cmd_colors_str = cmd_data.get('Color Identity', '')
        cmd_colors = str(cmd_colors_str).split(',') if pd.notna(cmd_colors_str) and str(cmd_colors_str).strip() != '' else []
        
        # Harten Filter anwenden
        def is_legal(card_color_str, cmd_colors_list):
            if pd.isna(card_color_str) or str(card_color_str).strip() == '': return True
            if not cmd_colors_list: return False
            return all(c in cmd_colors_list for c in str(card_color_str).split(','))

        df['Legal'] = df['Color Identity'].apply(lambda x: is_legal(x, cmd_colors))
        legal_pool = df[df['Legal'] == True]
        
        # Singleton & Standardländer
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        non_lands = legal_pool[~legal_pool['Name'].isin(basic_lands)].drop_duplicates(subset=['Name'])
        lands = legal_pool[legal_pool['Name'].isin(basic_lands)]
        pool_singleton = pd.concat([non_lands, lands])

        st.success(f"Dein legaler Kartenpool: {len(pool_singleton)} Karten.")
        
        st.subheader("2. KI-Deck generieren")
        api_key = st.text_input("OpenAI API-Key:", type="password")
        
        if st.button("Deck mit KI bauen") and api_key:
            openai.api_key = api_key
            
            # Wir bereiten die Daten für die KI vor (nur die wichtigsten Infos, um Tokens zu sparen)
            pool_for_ai = pool_singleton[['Name', 'Type Line', 'CMC', 'Oracle Text']].to_dict('records')
            
            prompt = f"""
            Du bist ein professioneller Magic: The Gathering Commander Deckbuilder.
            Dein Commander ist: {commander_name}.
            
            Baue ein 100-Karten Commander Deck (1 Commander + 99 Karten).
            Regeln:
            1. Du darfst AUSSCHLIESSLICH Karten aus dem folgenden Pool verwenden. Erfinde keine Karten!
            2. Wähle genau 99 Karten aus dem Pool.
            3. Achte auf eine gute Balance: ca. 36-38 Länder, 10 Ramp, 10 Card Draw, 10 Removal.
            4. Achte auf Synergien mit {commander_name}.
            
            Gib das Ergebnis als reines JSON-Objekt zurück mit dieser Struktur:
            {{
                "decklist": ["Kartenname 1", "Kartenname 2", ...],
                "strategy": "Kurze Beschreibung der Strategie",
                "manacurve_warning": "Hinweis, falls die Manakurve aus dem Pool nicht optimal ist"
            }}
            
            Hier ist der verfügbare Kartenpool:
            {json.dumps(pool_for_ai)}
            """
            
            with st.spinner("Die KI durchsucht deine Sammlung und baut Synergien... (Das dauert ca. 30-60 Sekunden)"):
                try:
                    response = openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={ "type": "json_object" }
                    )
                    
                                        result = json.loads(response.choices[0].message.content)
                    
                    st.write("### Strategie")
                    st.write(result.get("strategy", ""))
                    
                    decklist = result.get("decklist", [])
                    
                    # Zeige die Liste optisch etwas schöner an
                    st.write("### Deine Deckliste")
                    st.dataframe(pd.DataFrame({"Kartenname": decklist}))
                    
                    # -----------------------------------------
                    # NEU: Export-Funktion für ManaBox
                    # -----------------------------------------
                    if decklist:
                        # Füge "1 " vor jeden Kartennamen hinzu für das korrekte Import-Format
                        manabox_format = [f"1 {card}" for card in decklist]
                        # Füge den Commander noch als erste Karte hinzu
                        manabox_format.insert(0, f"1 {commander_name}")
                        
                        export_text = "\n".join(manabox_format)
                        
                        st.download_button(
                            label="📥 Deck für ManaBox herunterladen (.txt)",
                            data=export_text,
                            file_name=f"{commander_name.replace(' ', '_')}_deck.txt",
                            mime="text/plain"
                        )
                    
                except Exception as e:
                    st.error(f"Fehler bei der KI-Generierung: {e}")
