import streamlit as st
import pandas as pd
import sqlite3
import pickle
import os
if os.path.exists('food_data.db'):
    os.remove('food_data.db')

# --- 1. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('food_data.db')
    c = conn.cursor()
    # Updated table with Contact and Address
    c.execute('''CREATE TABLE IF NOT EXISTS items 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  donor TEXT, contact TEXT, address TEXT, 
                  food TEXT, qty TEXT, hours INT, status TEXT)''')
    conn.commit()
    conn.close()

# --- 2. LOAD AI BRAIN ---
@st.cache_resource
def load_model():
    return pickle.load(open('ai_brain_v2.pkl', 'rb'))

try:
    model = load_model()
except:
    st.error("Error: 'ai_brain_v2.pkl' not found. Please run your training script first!")

init_db()

# --- 3. UI SETUP ---
st.set_page_config(page_title="Smart Food Connector", page_icon="🍎", layout="wide")

# Sidebar Menu
st.sidebar.title("📌 Navigation")
menu = st.sidebar.radio("Select Role", ["🏠 Home Menu", "🍲 Food Donor", "🚚 NGO Dashboard"])

# --- 🏠 HOME MENU ---
if menu == "🏠 Home Menu":
    st.title("🍎 Smart Leftover Food Connector")
    st.markdown("### Bridging the gap between Waste and Want using AI.")
    st.info("👈 Select your role from the sidebar to get started.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("#### For Donors\nPost extra food from functions, hostels, or restaurants.")
    with col2:
        st.warning("#### For NGOs\nView real-time listings and claim food based on AI priority.")

# --- 🍲 FOOD DONOR PORTAL ---
elif menu == "🍲 Food Donor":
    st.title("🍲 Donor Portal")
    st.write("Provide details of the extra food. Our AI will analyze the spoilage risk.")
    
    with st.form("donor_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            donor = st.text_input("Donor Name / Org Name", placeholder="e.g. SRM Hostel Mess")
            contact = st.text_input("Contact Number", placeholder="e.g. +91 9876543210")
        with col_b:
            food = st.text_input("Food Item", placeholder="e.g. Veg Biryani")
            qty = st.text_input("Quantity", placeholder="e.g. 10 kg / 25 Plates")
        
        address = st.text_area("Pickup Address", placeholder="Enter full address for the NGO")
        hours = st.number_input("Hours since cooking", min_value=0, max_value=48, value=2)
        
        submit = st.form_submit_button("Analyze & Post Donation 🚀")

    if submit:
        # 1. AI INFERENCE
        input_df = pd.DataFrame([[food, hours]], columns=['food', 'hours'])
        prediction = model.predict(input_df)[0]
        prob = model.predict_proba(input_df)[0][prediction]
        conf = round(prob * 100, 1)

        # 2. STATUS ASSIGNMENT
        status = f"URGENT ({conf}% Risk)" if prediction == 1 else "AVAILABLE"
        
        # 3. SAVE TO DB
        conn = sqlite3.connect('food_data.db')
        c = conn.cursor()
        c.execute("INSERT INTO items (donor, contact, address, food, qty, hours, status) VALUES (?,?,?,?,?,?,?)", 
                  (donor, contact, address, food, qty, hours, status))
        conn.commit()
        conn.close()
        
        st.success(f"Listing Posted! AI analyzed this as: **{status}**")
        st.balloons()

# --- 🚚 NGO DASHBOARD ---
elif menu == "🚚 NGO Dashboard":
    st.title("🚚 NGO Dashboard")
    st.write("View available food items. Contact info is revealed only after claiming.")
    
    conn = sqlite3.connect('food_data.db')
    # We only show items that are NOT claimed yet
    df = pd.read_sql_query("SELECT id, donor, food, qty, hours, status FROM items WHERE status NOT LIKE 'CLAIMED%'", conn)
    
    if not df.empty:
        st.dataframe(df.drop(columns=['id']), use_container_width=True)
        
        st.divider()
        st.subheader("Action: Claim a Pickup")
        
        # Select item to claim
        options = {f"{row['food']} from {row['donor']}": row['id'] for _, row in df.iterrows()}
        selected_label = st.selectbox("Which item do you want to pick up?", list(options.keys()))
        selected_id = options[selected_label]
        
        if st.button("Claim Food & View Details ✅"):
            # Fetch full details including private info
            c = conn.cursor()
            c.execute("SELECT donor, contact, address, food FROM items WHERE id = ?", (selected_id,))
            details = c.fetchone()
            
            # Show Private Details
            st.warning("### 📍 DONOR CONTACT & ADDRESS REVEALED")
            st.markdown(f"**Donor:** {details[0]}")
            st.markdown(f"**Contact:** `{details[1]}`")
            st.markdown(f"**Address:** {details[2]}")
            st.info(f"Please reach the location for '{details[3]}' immediately.")
            
            # Mark as Claimed in DB
            c.execute("UPDATE items SET status = 'CLAIMED' WHERE id = ?", (selected_id,))
            conn.commit()
            st.rerun() # Refresh to update the table
    else:
        st.info("No active donations. All meals have been claimed! 🎉")
    conn.close()
