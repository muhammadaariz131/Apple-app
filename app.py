import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from streamlit_geolocation import streamlit_geolocation

# --- 1. DATABASE SETUP ---
def init_db():
    """Creates the database tables for all four logistics actions."""
    conn = sqlite3.connect('apple_harvest.db')
    c = conn.cursor()
    
    # We will use one unified table to track all movements
    c.execute('''
        CREATE TABLE IF NOT EXISTS logistics_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action_type TEXT,
            driver_name TEXT,
            location_name TEXT, 
            variety TEXT,
            quantity INTEGER,
            latitude REAL,
            longitude REAL,
            receipt_image BLOB
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(action_type, driver, location, variety, quantity, lat, lon, image_bytes):
    """Saves a new logistics record."""
    conn = sqlite3.connect('apple_harvest.db')
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO logistics_log (timestamp, action_type, driver_name, location_name, variety, quantity, latitude, longitude, receipt_image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (now, action_type, driver, location, variety, quantity, lat, lon, image_bytes))
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect('apple_harvest.db')
    df = pd.read_sql_query("SELECT * FROM logistics_log ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# Initialize database when the app starts
init_db()

# --- 2. APP CONFIGURATION ---
st.set_page_config(page_title="Apple Logistics", page_icon="🍎", layout="centered")

# Sidebar Navigation
st.sidebar.title("🍎 Apple Logistics")
app_mode = st.sidebar.radio("Select View:", ["📱 Driver App", "💻 Admin Dashboard"])
st.sidebar.markdown("---")
st.sidebar.info("Data saves automatically to the local database.")

# --- 3. DRIVER APP (MOBILE VIEW) ---
if app_mode == "📱 Driver App":
    st.title("Driver Dashboard")
    
    # The Four Core Actions
    action_type = st.selectbox("What action are you recording?", [
        "🍎 Pickup FILLED crates from Farm",
        "🏭 Drop FILLED crates at Cold Store",
        "🏭 Pickup EMPTY crates from Cold Store",
        "🍎 Drop EMPTY crates at Farm"
    ])
    
    st.divider()
    
    # Common Inputs for all actions
    driver_name = st.text_input("Driver Name", placeholder="Enter your full name")
    
    # Dynamic wording based on action
    if "Farm" in action_type:
        location_name = st.text_input("Farmer/Farm Name", placeholder="e.g., Ali Farm")
    else:
        location_name = st.text_input("Cold Store Name", placeholder="e.g., Main Cold Storage")
        
    st.write("📍 **Capture Location (Required)**")
    st.info("Tap the button below and allow Location access.")
    location_data = streamlit_geolocation()
        
    st.write("📸 **Take a Photo of the Receipt / Record**")
    receipt_photo = st.camera_input("Take Picture", key="cam_input")
    
    st.divider()

    # --- ACTION 1 & 2: Handling FILLED Crates (Requires Apple Variety) ---
    if "FILLED" in action_type:
        st.write("🍎 **Apple Load Details**")
        st.info("Click the empty row at the bottom of the table to add more varieties.")
        
        if "load_data" not in st.session_state:
            st.session_state.load_data = pd.DataFrame([{"Variety": "Galla", "Boxes": 0}])
            
        edited_df = st.data_editor(
            st.session_state.load_data,
            column_config={
                "Variety": st.column_config.SelectboxColumn("Apple Variety", options=["Galla", "Kullu", "Delicious", "Kullu delicious"], required=True),
                "Boxes": st.column_config.NumberColumn("Number of Boxes", min_value=1, step=1, required=True)
            },
            num_rows="dynamic", use_container_width=True, hide_index=True
        )
        
        if st.button(f"✅ Submit {action_type.split(' ')[1]}", type="primary", use_container_width=True):
            if not driver_name or not location_name:
                st.warning("⚠️ Please enter both your name and the location.")
            elif edited_df.empty or edited_df["Boxes"].sum() == 0:
                st.warning("⚠️ Please add at least one variety and quantity.")
            elif not receipt_photo:
                st.warning("⚠️ Please take a photo of the receipt.")
            elif not location_data or location_data.get('latitude') is None:
                st.warning("⚠️ Please tap the Location button to record your GPS coordinates.")
            else:
                real_lat = location_data['latitude']
                real_lon = location_data['longitude']
                img_bytes = receipt_photo.getvalue()
                
                for index, row in edited_df.iterrows():
                    if row["Boxes"] > 0:
                        insert_log(action_type, driver_name, location_name, row["Variety"], row["Boxes"], real_lat, real_lon, img_bytes)
                
                st.success(f"✅ Success! Data recorded.")
                st.session_state.load_data = pd.DataFrame([{"Variety": "Galla", "Boxes": 0}]) # Reset

    # --- ACTION 3 & 4: Handling EMPTY Crates (No Variety Needed) ---
    else:
        st.write("📦 **Empty Crate Details**")
        empty_crates = st.number_input("Total Empty Crates", min_value=1, step=1, value=50)
        
        if st.button(f"✅ Submit {action_type.split(' ')[1]}", type="primary", use_container_width=True):
             if not driver_name or not location_name:
                 st.warning("⚠️ Please enter both your name and the location.")
             elif not receipt_photo:
                 st.warning("⚠️ Please take a photo of the receipt.")
             elif not location_data or location_data.get('latitude') is None:
                 st.warning("⚠️ Please tap the Location button to record your GPS coordinates.")
             else:
                 real_lat = location_data['latitude']
                 real_lon = location_data['longitude']
                 img_bytes = receipt_photo.getvalue()
                 
                 insert_log(action_type, driver_name, location_name, "N/A (Empty)", empty_crates, real_lat, real_lon, img_bytes)
                 st.success(f"✅ Success! Data recorded.")


# --- 4. ADMIN DASHBOARD ---
elif app_mode == "💻 Admin Dashboard":
    st.title("Admin Dashboard")
    
    # 1. NEW LOGIN SYSTEM (Hides the password box after login)
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
        
    if not st.session_state.admin_logged_in:
        admin_pin = st.text_input("Enter Admin PIN", type="password")
        if admin_pin == "1234":
            st.session_state.admin_logged_in = True
            st.rerun() # Refreshes the page to hide the login box
        elif admin_pin:
            st.error("Incorrect PIN.")
        st.info("🔒 This section is restricted to Admin use only. PIN is 1234.")
        
    if st.session_state.admin_logged_in:
        # Show a logout button at the top
        col_logout_1, col_logout_2 = st.columns([0.8, 0.2])
        col_logout_1.success("Access Granted.")
        if col_logout_2.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
            
        df = load_data()
        
        if df.empty:
            st.info("No logistics data recorded yet.")
        else:
            # High-level metrics
            col1, col2, col3 = st.columns(3)
            
            # Filter data to calculate totals
            filled_pickups = df[df['action_type'].str.contains("Pickup FILLED")]['quantity'].sum()
            filled_drops = df[df['action_type'].str.contains("Drop FILLED")]['quantity'].sum()
            empty_tracked = df[df['action_type'].str.contains("EMPTY")]['quantity'].sum()
            
            col1.metric("Apples Picked Up", int(filled_pickups))
            col2.metric("Apples in Cold Store", int(filled_drops))
            col3.metric("Empty Crates Moved", int(empty_tracked))
            
            st.divider()
            
            # Map View
            st.subheader("📍 Live Fleet Map")
            # We filter out rows without coordinates just in case
            map_df = df.dropna(subset=['latitude', 'longitude'])
            if not map_df.empty:
                st.map(map_df, size=150, color="#FF0000")
            
            st.divider()
            
            # Detailed Data Grid with Filters
            st.subheader("📋 Comprehensive Logistics Log")
            
            filter_action = st.selectbox("Filter by Action:", ["All"] + list(df['action_type'].unique()))
            if filter_action != "All":
                display_df = df[df['action_type'] == filter_action]
            else:
                display_df = df
                
            # Exclude the receipt image BLOB from the visual table, as it crashes the dataframe view
            display_df = display_df[['timestamp', 'action_type', 'driver_name', 'location_name', 'variety', 'quantity']]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # --- 2. NEW RECEIPT VIEWER ---
            st.divider()
            st.subheader("📸 Receipt Viewer")
            st.info("Select a log entry below to view its captured receipt photo.")
            
            # Create a clean label for the dropdown menu so you know which photo you are looking at
            df['receipt_label'] = df['timestamp'] + " | " + df['driver_name'] + " (" + df['action_type'] + ")"
            
            selected_entry = st.selectbox("Select a pickup/drop record:", df['receipt_label'].tolist())
            
            if selected_entry:
                # Find the exact row the user selected
                row_data = df[df['receipt_label'] == selected_entry].iloc[0]
                
                # Check if an image actually exists for this row
                if pd.notna(row_data['receipt_image']) and row_data['receipt_image'] is not None:
                    st.image(row_data['receipt_image'], caption=f"Receipt uploaded by {row_data['driver_name']} at {row_data['location_name']}", use_container_width=True)
                else:
                    st.warning("No photo was uploaded for this specific record.")