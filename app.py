import streamlit as st
import pandas as pd

st.set_page_config(page_title="Magic Commander Builder", layout="wide")

st.title("🧙‍♂️ Magic Commander Deck Builder")
st.write("Lade deine angereicherte Sammlung hoch, um deinen Commander zu wählen.")

# Datei-Upload-Feld für die CSV
uploaded_file = st.file_uploader("master_collection.csv hochladen", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # 1. Alle Legendären Kreaturen finden
    commanders = df[df['Is Legendary'] == True]
    
    st.subheader("1. Wähle deinen Commander")
    commander_name = st.selectbox("Commander auswählen:", commanders['Name'].sort_values())
    
    if commander_name:
        # Commander-Farben auslesen
        cmd_data = commanders[commanders['Name'] == commander_name].iloc[0]
        cmd_colors_str = cmd_data.get('Color Identity', '')
        
        if pd.isna(cmd_colors_str) or str(cmd_colors_str).strip() == '':
            cmd_colors = []
            st.write("**Farbidentität:** Farblos ⚙️")
        else:
            cmd_colors = str(cmd_colors_str).split(',')
            st.write(f"**Farbidentität:** {', '.join(cmd_colors)}")
            
        # 2. Harten Filter anwenden (Commander-Regel: Nur Karten in Commander-Farben)
        def is_legal(card_color_str, cmd_colors_list):
            if pd.isna(card_color_str) or str(card_color_str).strip() == '':
                return True # Farblose Karten sind überall legal
            if not cmd_colors_list: 
                return False # Wenn Commander farblos, keine farbigen Karten erlaubt
            card_colors = str(card_color_str).split(',')
            return all(c in cmd_colors_list for c in card_colors)

        df['Legal'] = df['Color Identity'].apply(lambda x: is_legal(x, cmd_colors))
        legal_pool = df[df['Legal'] == True]
        
        # Singleton-Regel: Keine doppelten Karten außer Standard-Ländern
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        non_lands = legal_pool[~legal_pool['Name'].isin(basic_lands)].drop_duplicates(subset=['Name'])
        lands = legal_pool[legal_pool['Name'].isin(basic_lands)]
        pool_singleton = pd.concat([non_lands, lands])

        st.success(f"Dein legaler Kartenpool: {len(pool_singleton)} Karten aus deiner Sammlung passen zu diesem Commander.")
        
        # Tabelle anzeigen
        st.dataframe(pool_singleton[['Name', 'Type Line', 'CMC', 'Color Identity', 'Purchase price']])
        
        # Vorbereitung für den KI-Schritt
        st.subheader("2. KI-Deck generieren")
        api_key = st.text_input("OpenAI API-Key:", type="password")
        if st.button("Deck mit KI bauen"):
            st.info("Das Interface steht! Als nächstes klemmen wir hier die OpenAI-Logik an.")
