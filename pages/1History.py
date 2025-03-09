import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Set page title
st.set_page_config(page_title="Exercise History", layout="wide")

# Database connection function
def fetch_data(filters):
    """Fetches filtered exercise data from the database."""
    conn = sqlite3.connect("exercise.db")
    query = "SELECT * FROM exercise_table WHERE 1=1"
    params = []
    
    # Apply filters
    if filters["start_date"]:
        query += " AND Datetime >= ?"
        params.append(filters["start_date"])
    
    if filters["end_date"]:
        query += " AND Datetime <= ?"
        params.append(filters["end_date"])
    
    if filters["exercise_type"]:
        query += " AND Exercise_Type = ?"
        params.append(filters["exercise_type"])
    
    if filters["exercise_id"]:
        query += " AND ID = ?"
        params.append(filters["exercise_id"])
    
    query += " ORDER BY Datetime DESC"
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df

def delete_data(filters):
    """Deletes exercise data and associated photos based on filters."""
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    
    # Fetch IDs of records to delete (to remove associated photos)
    select_query = "SELECT ID FROM exercise_table WHERE 1=1"
    delete_query = "DELETE FROM exercise_table WHERE 1=1"
    params = []

    if filters["start_date"]:
        select_query += " AND Datetime >= ?"
        delete_query += " AND Datetime >= ?"
        params.append(filters["start_date"])
    
    if filters["end_date"]:
        select_query += " AND Datetime <= ?"
        delete_query += " AND Datetime <= ?"
        params.append(filters["end_date"])
    
    if filters["exercise_type"]:
        select_query += " AND exercise_Type = ?"
        delete_query += " AND exercise_Type = ?"
        params.append(filters["exercise_type"])
    
    if filters["exercise_id"]:
        select_query += " AND ID = ?"
        delete_query += " AND ID = ?"
        params.append(filters["exercise_id"])

    # Fetch records to delete
    cursor.execute(select_query, params)
    records_to_delete = cursor.fetchall()

    # Delete corresponding photos
    for record in records_to_delete:
        exercise_id = record[0]  # Extract ID
        photo_path = os.path.join("Photos", f"{exercise_id}.jpg")
        if os.path.exists(photo_path):
            os.remove(photo_path)
            print(f"🗑️ Deleted photo: {photo_path}")

    # Only execute DELETE if there are filters (to prevent accidental full table deletion)
    if params:
        cursor.execute(delete_query, params)
        deleted_rows = cursor.rowcount  # Number of deleted records
        conn.commit()
    else:
        deleted_rows = 0  # No deletion happened

    conn.close()
    return deleted_rows

# Sidebar for filters
st.sidebar.title("🔍 Search Exercise History")

# Date filter
start_date = st.sidebar.date_input("Start Date", value=None)
end_date = st.sidebar.date_input("End Date", value=None)

# Convert to proper format
start_date = datetime.combine(start_date, datetime.min.time()) if start_date else None
end_date = datetime.combine(end_date, datetime.max.time()) if end_date else None

# Exercise type filter
exercise_type = st.sidebar.text_input("Exercise Type (Optional)")

# ID filter
exercise_id = st.sidebar.text_input("Exercise ID (Optional)")

# Fetch data based on filters
filters = {
    "start_date": start_date,
    "end_date": end_date,
    "exercise_type": exercise_type.strip(),
    "exercise_id": exercise_id.strip() if exercise_id.isdigit() else None
}

df = fetch_data(filters)

# UI Header
st.markdown("<h1 style='text-align: center; color: #007BFF;'>📜 Exercise History</h1>", unsafe_allow_html=True)

if not df.empty:
    df["Datetime"] = pd.to_datetime(df["Datetime"])  # Convert to datetime format
    df["Date"] = df["Datetime"].dt.date
    df["Time"] = df["Datetime"].dt.time

    # Display Data
    st.write("### 📝 Exercise Records Found")
    st.dataframe(df[["ID", "Date", "Time", "Count", "Exercise_Type"]], height=300, use_container_width=True, hide_index=True)

    # Show images (if available)
    st.write("### 📸 Exercise Photos")

    photo_found = False  # Flag to check if at least one photo exists

    for exercise_id in df["ID"]:
        photo_path = os.path.join("Photos", f"{exercise_id}.jpg")
        if os.path.exists(photo_path):
            col1, col2, col3 = st.columns([1, 2, 1])  # Creates three columns
            with col2:  # Use the middle column
                st.image(photo_path, caption=f"Exercise ID: {exercise_id}", width=1000)
            photo_found = True

    # If no photos were found, show a single message
    if not photo_found:
        st.warning("❌ No photos available for the selected exercises.")

    # --- DELETE FUNCTIONALITY ---
    st.write("### ⚠️ Delete Exercise Entries")

    if st.button("🗑️ Delete Selected Entries"):
        st.session_state.confirm_delete = True  # Set confirmation flag
    
    if st.session_state.get("confirm_delete", False):
        st.warning("⚠️ Are you sure you want to delete the selected records? This action cannot be undone.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete"):
                deleted_count = delete_data(filters)
                st.session_state.confirm_delete = False  # Reset flag
                st.success(f"🗑️ Successfully deleted {deleted_count} records.")
                st.rerun()
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.confirm_delete = False  # Reset flag

else:
    st.write("### 🚨 No matching records found.")
    st.write("Try adjusting your filters to find relevant exercises.")

# Footer
st.markdown("""
    <style>
        .footer {position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background-color: #f8f9fa; color: #6c757d;}
    </style>
    <div class="footer">🚀 Built with Streamlit</div>
""", unsafe_allow_html=True)
