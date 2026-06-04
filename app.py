import streamlit as st
import pandas as pd
import openai
import json

# App Layout Konfiguration
st.set_page_config(page_title="Magic Commander Builder", layout="wide")

st.title("🧙‍♂️ Magic Commander Deck Builder")
st.write("Lade deine angereicherte Sammlung hoch, um deinen Commander zu wählen.")

# Datei-Upload-Feld
uploaded_file = st.file_uploader("master_collection.csv hochladen", type=["csv"])

if uploaded_file is not None:
    # Daten einlesen
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
        
        # Singleton & Standardländer (Doppelte Karten aus der Sammlung filtern)
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        non_lands = legal_pool[~legal_pool['Name'].isin(basic_lands)].drop_duplicates(subset=['Name'])
        lands = legal_pool[legal_pool['Name'].isin(basic_lands)]
        pool_singleton = pd.concat([non_lands, lands])

        st.success(f"Dein legaler Kartenpool: {len(pool_singleton)} Karten aus deiner Sammlung passen zu diesem Commander.")
        
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
                    st.write(f"### Deine Deckliste ({len(decklist)} Karten)")
                    
                    # -----------------------------------------------------
                    # NEU: Das aufgeräumte 3-Spalten-Layout nach Kartentyp
                    # -----------------------------------------------------
                    
                    # Generierte Karten mit den CSV-Metadaten matchen
                    deck_df = pool_singleton[pool_singleton['Name'].isin(decklist)]
                    
                    def get_main_type(type_line):
                        t = str(type_line).lower()
                        if 'land' in t: return 'Länder'
                        elif 'creature' in t: return 'Kreaturen'
                        elif 'artifact' in t: return 'Artefakte'
                        elif 'enchantment' in t: return 'Verzauberungen'
                        elif 'planeswalker' in t: return 'Planeswalker'
                        elif 'instant' in t: return 'Instants'
                        elif 'sorcery' in t: return 'Sorceries'
                        else: return 'Sonstiges'
                    
                    deck_df['Main Type'] = deck_df['Type Line'].apply(get_main_type)
                    
                    # 3 Spalten erstellen
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        creatures = deck_df[deck_df['Main Type'] == 'Kreaturen']
                        st.markdown(f"#### Kreaturen ({len(creatures)})")
                        st.dataframe(creatures[['Name', 'CMC']].sort_values('CMC'), hide_index=True)
                        
                        planeswalkers = deck_df[deck_df['Main Type'] == 'Planeswalker']
                        if not planeswalkers.empty:
                            st.markdown(f"#### Planeswalker ({len(planeswalkers)})")
                            st.dataframe(planeswalkers[['Name', 'CMC']], hide_index=True)
                            
                    with col2:
                        artifacts = deck_df[deck_df['Main Type'] == 'Artefakte']
                        st.markdown(f"#### Artefakte ({len(artifacts)})")
                        st.dataframe(artifacts[['Name', 'CMC']].sort_values('CMC'), hide_index=True)
                        
                        enchantments = deck_df[deck_df['Main Type'] == 'Verzauberungen']
                        if not enchantments.empty:
                            st.markdown(f"#### Verzauberungen ({len(enchantments)})")
                            st.dataframe(enchantments[['Name', 'CMC']].sort_values('CMC'), hide_index=True)
                            
                    with col3:
                        instants = deck_df[deck_df['Main Type'] == 'Instants']
                        st.markdown(f"#### Instants ({len(instants)})")
                        st.dataframe(instants[['Name', 'CMC']].sort_values('CMC'), hide_index=True)
                        
                        sorceries = deck_df[deck_df['Main Type'] == 'Sorceries']
                        st.markdown(f"#### Sorceries ({len(sorceries)})")
                        st.dataframe(sorceries[['Name', 'CMC']].sort_values('CMC'), hide_index=True)
                        
                        lands_df = deck_df[deck_df['Main Type'] == 'Länder']
                        st.markdown(f"#### Länder ({len(lands_df)})")
                        st.dataframe(lands_df[['Name']].sort_values('Name'), hide_index=True)

                    st.divider() # Optische Trennlinie
                    
                    # -----------------------------------------------------
                    # Der ManaBox Export
                    # -----------------------------------------------------
                    if decklist:
                        manabox_format = [f"1 {card}" for card in decklist]
                        manabox_format.insert(0, f"1 {commander_name}") # Commander hinzufügen
                        
                        export_text = "\n".join(manabox_format)
                        
                        st.download_button(
                            label="📥 Deck für ManaBox herunterladen (.txt)",
                            data=export_text,
                            file_name=f"{commander_name.replace(' ', '_')}_deck.txt",
                            mime="text/plain"
                        )
                    
                except Exception as e:
                    st.error(f"Fehler bei der KI-Generierung: {e}")
