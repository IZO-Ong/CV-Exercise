import streamlit as st
import sqlite3
import random
import os
from datetime import datetime, timedelta
import shutil

PHOTOS_FOLDER = "Photos"  # Folder containing images

def add_manual_entry(exercise_type, count, datetime_str):
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO exercise_table (Datetime, Count, exercise_Type) VALUES (?, ?, ?)",
                   (datetime_str, count, exercise_type))
    conn.commit()
    conn.close()

def add_random_entries(num_entries):
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    
    for _ in range(num_entries):
        random_days_ago = random.randint(0, 365)
        random_time = random.randint(9 * 60, 22 * 60)
        random_datetime = datetime.now() - timedelta(days=random_days_ago, minutes=random_time)
        formatted_datetime = random_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")
        count = random.randint(1, 40)
        exercise_type = random.choice(["Squat", "Push Up"])
        cursor.execute("INSERT INTO exercise_table (Datetime, Count, exercise_Type) VALUES (?, ?, ?)",
                       (formatted_datetime, count, exercise_type))
    
    conn.commit()
    conn.close()

def delete_all_entries_and_photos():
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    try:
        cursor.execute("DELETE FROM exercise_table")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='exercise_table'")
        conn.commit()
        cursor.execute("VACUUM")  # Optimize database after deletion
    except sqlite3.Error as e:
        print("Error:", e)
        conn.rollback()
    finally:
        conn.close()

    if os.path.exists(PHOTOS_FOLDER):
        try:
            shutil.rmtree(PHOTOS_FOLDER)
            os.makedirs(PHOTOS_FOLDER)  # Recreate the empty folder
        except Exception as e:
            print("Error deleting photos:", e)

st.set_page_config(page_title="Exercise Tracker", layout="centered")
st.title("🏋️ Exercise Tracker Dashboard")

st.markdown("### Manage your exercise records with ease!")

st.subheader("📝 Add Manual Entry")
col1, col2 = st.columns(2)
exercise_type = col1.selectbox("Exercise Type", ["Push Up", "Squat"], index=0)
count = col2.number_input("Number of Counts", min_value=1, max_value=500, value=10, step=1)

date_selected = st.date_input("Select Date", value=datetime.today())

if "time_selected" not in st.session_state:
    st.session_state.time_selected = datetime.now().time()

time_selected = st.time_input("Select Time", value=st.session_state.time_selected)
st.session_state.time_selected = time_selected

selected_datetime = datetime.combine(date_selected, time_selected).strftime("%Y-%m-%d %H:%M:%S.%f")

if st.button("➕ Add Entry", use_container_width=True):
    add_manual_entry(exercise_type, count, selected_datetime)
    st.success(f"✅ Added: {exercise_type} - {count} counts on {selected_datetime}")

st.markdown("---")

st.subheader("➕ Add Random Entries")
if "confirm_random" not in st.session_state:
    st.session_state.confirm_random = False
if "random_success" not in st.session_state:
    st.session_state.random_success = False

num_entries = st.slider("Number of Random Entries", min_value=1, max_value=100, value=10)
if st.button("Generate Random Data", use_container_width=True):
    st.session_state.confirm_random = True

if st.session_state.get("confirm_random", False):
    if st.button("Yes, generate random data"):
        add_random_entries(num_entries)
        st.session_state.random_success = True
        st.session_state.confirm_random = False

if st.session_state.random_success:
    st.success(f"✅ {num_entries} random entries added successfully!")

st.markdown("---")

st.subheader("❌ Delete All Entries & Photos")
if "delete_success" not in st.session_state:
    st.session_state.delete_success = False

if st.button("Delete All Data and Photos", use_container_width=True, key="delete_data"):
    st.session_state.confirm_delete = True

if st.session_state.get("confirm_delete", False):
    if st.button("Yes, delete everything"):
        delete_all_entries_and_photos()
        st.session_state.delete_success = True
        st.session_state.confirm_delete = False

if st.session_state.delete_success:
    st.warning("🗑️ All records and photos deleted successfully!")