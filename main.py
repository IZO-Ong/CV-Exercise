import sqlite3
import os
import altair as alt
import streamlit as st
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase

# Initialize database
def initialize_db():
    conn = sqlite3.connect("physio.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS physio_table (
                        ID INTEGER PRIMARY KEY AUTOINCREMENT,
                        Datetime DATETIME,
                        Count INTEGER,
                        Physio_Type TEXT)''')
    conn.commit()
    conn.close()

initialize_db()

def start_sql_db():
    db = SQLDatabase.from_uri("sqlite:///physio.db")
    return db

# Set page title and layout
st.set_page_config(page_title="Physio Tracker", layout="wide")

# Initialize the database
db = start_sql_db()

# Sidebar for filters
st.sidebar.title("Filters")

# Fetch data from database
conn = sqlite3.connect("physio.db")
cursor = conn.cursor()
cursor.execute("SELECT * FROM physio_table ORDER BY Datetime;")
data = cursor.fetchall()
conn.close()

# Define column names
df = pd.DataFrame(data, columns=["ID", "Datetime", "Count", "Physio_Type"])

# Check if the DataFrame is empty, and convert 'Datetime' column only if it's not empty
if not df.empty:
    df["Datetime"] = pd.to_datetime(df["Datetime"]) # Convert the 'Datetime' column to datetime format
    
    # Allow user to filter by date range
    start_date = st.sidebar.date_input("Start Date", df["Datetime"].min().date())
    end_date = st.sidebar.date_input("End Date", df["Datetime"].max().date())

    # Convert to timestamps ensuring full end-of-day inclusion
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)  # Set to 23:59:59

    # Filter data based on date range
    df = df[(df["Datetime"] >= start_date) & (df["Datetime"] <= end_date)]

    # Allow filtering by Physio Type
    physio_types = st.sidebar.multiselect("Select Physio Types", df["Physio_Type"].unique(), default=df["Physio_Type"].unique())

    # Apply filter
    df = df[df["Physio_Type"].isin(physio_types)]
else:
    start_date = st.sidebar.date_input("Start Date")
    end_date = st.sidebar.date_input("End Date")

# --- UI Header ---
st.markdown("<h1 style='text-align: center; color: #007BFF;'>🏋️‍♂️ Physio Exercise Tracker</h1>", unsafe_allow_html=True)
st.write("### Track and visualise your exercise history with insights into trends over time.")

# --- Display Data Table ---
df_display = df.copy()
df_display = df_display.sort_values(by="Datetime", ascending=False)
df_display = df_display.head(5)

# Split Datetime into Date and Time only if 'Datetime' column exists
if not df.empty:
    df_display["Date"] = df_display["Datetime"].dt.date
    df_display["Time"] = df_display["Datetime"].dt.time

    # Drop ID and Datetime columns for display
    df_display = df_display[["Date", "Time", "Count", "Physio_Type"]]

    # Display the modified DataFrame
    st.write("### 📝 Recent Exercise Records")
    st.dataframe(df_display, height=250, use_container_width=True, hide_index=True)
else:
    st.write("### 🚨 No data available.")
    st.write("It seems like there are no records for the selected filters. Please check the options below:")
    st.write("- **Database Tab**: You can generate random entries in the database.")
    st.write("- **Tracker Tab**: Record new entries for your exercise sessions.")

# --- Aggregate Data for Chart ---
if not df.empty:
    df["Date"] = df["Datetime"].dt.date  # Create a new Date column explicitly
    df_grouped = df.groupby(["Date", "Physio_Type"], as_index=False)["Count"].sum()
else:
    df_grouped = pd.DataFrame(columns=["Date", "Physio_Type", "Count"])  # Create an empty DataFrame

# Use Altair for better visualization
if not df_grouped.empty:
    chart = alt.Chart(df_grouped).mark_line(point=True).encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Count:Q", title="Total Count"),
        color="Physio_Type:N",
        tooltip=["Date", "Physio_Type", "Count"]
    ).properties(
        width=800,
        height=400,
        title="📊 Physio Exercise Trends"
    ).interactive()

    st.altair_chart(chart, use_container_width=True)
    
if not df_grouped.empty:
    # Set up OpenAI API key and model
    try:
        open_ai_key = os.getenv("OPENAI_KEY")
    except:
        st.write("To use the Physio Assistant function, please include your Open AI key in a .env file")
    else:
        os.environ["OPENAI_API_KEY"] = open_ai_key
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Convert recent exercise data to a dictionary format
        recent_exercise_data = df_display.to_dict(orient="records")

        # Prepare the prompt to be passed to OpenAI
        prompt = f"""
        You are a friendly physio exercise assistant. Based on the following recent exercise data, provide a brief comment and some insights:
        
        Recent Exercise Records:
        {recent_exercise_data}

        Provide the user with helpful and friendly comments on their exercise history. You can mention patterns, improvements, or trends.
        """

        # Use OpenAI model to generate the comment
        with st.status("💭 Physio Assistant is thinking..."):
            response = llm.invoke([prompt])  # Use invoke with the prompt

        # Display the generated response
        st.write("### 🗨️ Insights from Physio Assistant")
        st.write(response.content)

# --- Footer ---
st.markdown("""
    <style>
        .footer {position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background-color: #f8f9fa; color: #6c757d;}
    </style>
    <div class="footer">🚀 Built with using Streamlit</div>
""", unsafe_allow_html=True)
