import streamlit as st
import sqlite3
import random
import os
from datetime import datetime, timedelta

PHOTOS_FOLDER = "Photos"  # Folder containing images

# Function to insert random entries
def add_random_entries(num_entries):
    conn = sqlite3.connect("physio.db")
    cursor = conn.cursor()
    
    for _ in range(num_entries):
        # Generate random date/time within the last year, including microseconds
        random_days_ago = random.randint(0, 365)
        random_time = random.randint(9 * 60, 22 * 60)  # Minutes from 9 AM to 10 PM
        random_datetime = datetime.now() - timedelta(days=random_days_ago, minutes=random_time)
        
        # Format the datetime with microseconds
        formatted_datetime = random_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        
        # Generate random count and type
        count = random.randint(1, 40)
        physio_type = random.choice(["Squat", "Push Up"])
        
        # Insert into table with the correctly formatted datetime
        cursor.execute("INSERT INTO physio_table (Datetime, Count, Physio_Type) VALUES (?, ?, ?)",
                       (formatted_datetime, count, physio_type))
    
    conn.commit()
    conn.close()

# Function to delete all entries and images
def delete_all_entries_and_photos():
    # Connect to the database
    conn = sqlite3.connect("physio.db")
    cursor = conn.cursor()
    
    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON;")

    try:
        # Delete all records from the table
        cursor.execute("DELETE FROM physio_table")
        
        # Reset the autoincrement ID (if necessary)
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='physio_table'")

        # Commit changes
        conn.commit()
    except sqlite3.Error as e:
        print("Error:", e)
        conn.rollback()  # Rollback in case of error
    finally:
        # Close the connection
        conn.close()


    # Delete all images from the "Photos" folder
    if os.path.exists(PHOTOS_FOLDER):
        for file in os.listdir(PHOTOS_FOLDER):
            file_path = os.path.join(PHOTOS_FOLDER, file)
            if os.path.isfile(file_path) and file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                os.remove(file_path)

# Streamlit UI
st.set_page_config(page_title="Physio Tracker", layout="centered")
st.title("🏋️ Physio Tracker Dashboard")

st.markdown("### Manage your physiotherapy records with ease!")

# User input for adding random entries
st.subheader("➕ Add Random Entries")
num_entries = st.number_input("How many random entries to add?", min_value=1, max_value=1000, value=10, step=1)

# Check if user has already clicked the button and confirmed
if "confirm_add" not in st.session_state:
    st.session_state.confirm_add = False

if st.button("Generate Random Data"):
    # Set flag to indicate the user has clicked the button for confirmation
    st.session_state.confirm_add = True
    st.error("⚠️ Are you sure you want to add these records?")
    
if st.session_state.confirm_add:
    if st.button("Yes, add the records"):
        add_random_entries(num_entries)
        st.session_state.confirm_add = False  # Reset flag after action
        st.success(f"✅ {num_entries} random entries added successfully!")

# Divider
st.markdown("---")

# Button to delete all entries and photos
st.subheader("❌ Delete All Entries & Photos")
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

if st.button("Delete All Data and Photos", key="delete_data"):
    st.session_state.confirm_delete = True
    st.error("⚠️ This will delete all records and photos permanently. Are you sure?")

if st.session_state.confirm_delete:
    if st.button("Yes, delete everything"):
        delete_all_entries_and_photos()
        st.session_state.confirm_delete = False  # Reset flag after action
        st.warning("🗑️ All records and photos deleted successfully!")
