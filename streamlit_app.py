import streamlit as st
import pandas as pd
import sqlite3
import pickle
from datetime import datetime

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('food_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (donor TEXT, food TEXT, qty TEXT, hours INT, status TEXT)''')
    conn.commit()
    conn.close()

# --- LOAD AI BRAIN ---
@st.cache_resource
def load_model():
    return pickle.load(open('ai_brain_v2.pkl', 'rb'))

model = load_model()
init_db()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Smart Food Connector", page_icon="🍎")

st.title("🍎 Smart Leftover Food Connector")
st.markdown("AI-Powered Food Waste Reduction Platform")

# SIDEBAR MENU
menu = st.sidebar.selectbox("Select Role", ["🏠 Home/Menu", "🍲 Food Donor", "🚚 NGO Dashboard"])

if menu == "🏠 Home/Menu":
    st.subheader("Welcome!")
    st.write("This platform uses Machine Learning to predict food spoilage risk and connect donors with NGOs.")
    st.info("Choose a role from the sidebar to get started.")

elif menu == "🍲 Food Donor":
    st.subheader("Post a Food Donation")
    with st.form("donation_form"):
        donor = st.text_input("Your Name / Organization")
        food = st.text_input("Food Item (e.g. Rice, Curry)")
        qty = st.text_input("Quantity (e.g. 5kg)")
        hours = st.number_input("Hours since cooking", min_value=0, max_value=48, value=1)
        submit = st.form_submit_button("Analyze & Post")

    if submit:
        # AI PREDICTION
        input_df = pd.DataFrame([[food, hours]], columns=['food', 'hours'])
        prediction = model.predict(input_df)[0]
        prob = model.predict_proba(input_df)[0][prediction]
        
        status = f"URGENT ({round(prob*100)}% Risk)" if prediction == 1 else "AVAILABLE"
        
        # Save to DB
        conn = sqlite3.connect('food_data.db')
        c = conn.cursor()
        c.execute("INSERT INTO items VALUES (?,?,?,?,?)", (donor, food, qty, hours, status))
        conn.commit()
        conn.close()
        
        st.success(f"Posted! AI Result: {status}")

elif menu == "🚚 NGO Dashboard":
    st.subheader("Available Food for Pickup")
    conn = sqlite3.connect('food_data.db')
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()

    if not df.empty:
        # Show table with color coding
        st.table(df)
        
        # Simple Claim Logic
        item_to_claim = st.selectbox("Select Food Item to Claim", df['food'].tolist())
        if st.button("Claim Pickup"):
            st.success(f"You have claimed {item_to_claim}. Please contact the donor.")
    else:
        st.write("No food available right now. Check back later!")