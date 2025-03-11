import sqlite3
import os
import altair as alt
import streamlit as st
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase

# Initialize database
def initialize_db():
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_table (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Datetime DATETIME,
                        Count INTEGER,
                        Exercise_Type TEXT)''')
    conn.commit()
    conn.close()

initialize_db()

def start_sql_db():
    db = SQLDatabase.from_uri("sqlite:///exercise.db")
    return db

# Set page title and layout
st.set_page_config(page_title="Exercise Tracker", layout="wide")

# Initialize the database
db = start_sql_db()

# Sidebar for filters
st.sidebar.title("Filters")

# Fetch data from database
conn = sqlite3.connect("exercise.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM exercise_table ORDER BY Datetime;")
data = cursor.fetchall()
conn.close()

# Define column names
df = pd.DataFrame(data, columns=["ID", "Datetime", "Count", "Exercise_Type"])

# Check if the DataFrame is empty
if not df.empty:
    df["Datetime"] = pd.to_datetime(df["Datetime"])  # Convert to datetime
    df["Date"] = df["Datetime"].dt.date  # Extract date

    # Get min and max dates
    min_date = df["Date"].min()
    max_date = df["Date"].max()
    
    # User-selected date range
    start_date = st.sidebar.date_input("Start Date", min_date)
    end_date = st.sidebar.date_input("End Date", max_date)

    # Convert to timestamps
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    # Filter data by date range
    df = df[(df["Datetime"] >= start_date) & (df["Datetime"] <= end_date)]

    # Allow filtering by exercise type
    exercise_types = st.sidebar.multiselect("Select Exercise Types", df["Exercise_Type"].unique(), default=df["Exercise_Type"].unique())
    df = df[df["Exercise_Type"].isin(exercise_types)]
else:
    start_date = st.sidebar.date_input("Start Date")
    end_date = st.sidebar.date_input("End Date")

# --- Display Data Table ---
if not df.empty:
    df_display = df.sort_values(by="Datetime", ascending=False).head(5)
    df_display["Date"] = df_display["Datetime"].dt.date
    df_display["Time"] = df_display["Datetime"].dt.time
    df_display = df_display[["Date", "Time", "Count", "Exercise_Type"]]
    st.write("### 📝 Recent Exercise Records")
    st.dataframe(df_display, height=250, use_container_width=True, hide_index=True)
else:
    st.write("### 🚨 No data available.")

# --- Aggregate Data for Chart ---
if not df.empty:
    df_grouped = df.groupby(["Date", "Exercise_Type"], as_index=False)["Count"].sum()
    
    # Ensure all dates in the range are included
    all_dates = pd.date_range(start=min_date, end=max_date).date
    all_exercises = df["Exercise_Type"].unique()
    full_index = pd.MultiIndex.from_product([all_dates, all_exercises], names=["Date", "Exercise_Type"])
    df_grouped = df_grouped.set_index(["Date", "Exercise_Type"]).reindex(full_index, fill_value=0).reset_index()

    # Use Altair for visualization
    chart = alt.Chart(df_grouped).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Count:Q", title="Total Count", scale=alt.Scale(zero=True)),
        color="Exercise_Type:N",
        tooltip=["Date", "Exercise_Type", "Count"]
    ).properties(
        width=800,
        height=400,
        title="📊 Exercise Trends"
    ).interactive()
    st.altair_chart(chart, use_container_width=True)

# --- Footer ---
st.markdown("""
    <style>
        .footer {position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background-color: #f8f9fa; color: #6c757d;}
    </style>
    <div class="footer">🚀 Built with using Streamlit</div>
""", unsafe_allow_html=True)