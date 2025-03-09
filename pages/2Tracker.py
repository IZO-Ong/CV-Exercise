import cv2
import streamlit as st
import sqlite3
import datetime
import os
from ultralytics import solutions, YOLO

# Initialize YOLO model
model = YOLO("yolo11n-pose.pt")

# Define keypoints for different exercises
keypoints_dict = {"squat": [5, 11, 13], "pushup": [5, 7, 9]}

def save_workout(count, workout_type):
    """Save workout data to the database."""
    conn = sqlite3.connect("exercise.db")
    cursor = conn.cursor()
    now = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO exercise_table (datetime, count, exercise_type) VALUES (?, ?, ?)",
        (now, count, workout_type)
    )
    session_id = cursor.lastrowid  # Get session ID
    conn.commit()
    conn.close()
    return session_id

def save_frame(image, session_id):
    """Save a snapshot of the best frame from the workout."""
    photos_dir = "Photos"
    os.makedirs(photos_dir, exist_ok=True)
    image_path = os.path.join(photos_dir, f"{session_id}.jpg")
    cv2.imwrite(image_path, image)
    return image_path

def start_workout(workout_type):
    """Start real-time workout detection."""
    st.session_state.data_saved = False
    st.session_state.workout_count = 0
    st.session_state.best_frame = None
    st.session_state.workout_type = workout_type

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        st.error("❌ Error accessing webcam")
        return

    gym = solutions.AIGym(show=False, kpts=keypoints_dict[workout_type], model="yolo11n-pose.pt", line_width=2, verbose=False, down_angle = 100.0)

    best_frame = None

    # Create window and set it to always be on top
    cv2.namedWindow("Workout Counter", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Workout Counter", cv2.WND_PROP_TOPMOST, 1)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            st.write("⚠️ Error reading frame from webcam.")
            break

        frame = gym.monitor(frame)
        st.session_state.workout_count = gym.count[0]
        if best_frame is None and gym.count[0] == 1:
            best_frame = frame.copy()

        cv2.putText(frame, "Press 'Q' to Exit", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
        cv2.imshow("Workout Counter", frame)
        cv2.setWindowProperty("Workout Counter", cv2.WND_PROP_TOPMOST, 1)  # Keep forcing it on top

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    st.session_state.best_frame = best_frame

def main():
    st.set_page_config(page_title="Workout Tracker", layout="centered")
    st.title("🏋️ AI-Powered Workout Counter")
    st.markdown("Track your exercises in real-time using AI-powered detection.")
    st.warning("⚠️ Ensure that your body can be fully seen throughout the session for accurate counting.")
    
    # Initialize session state variables if not present
    if "workout_count" not in st.session_state:
        st.session_state.workout_count = 0
    if "data_saved" not in st.session_state:
        st.session_state.data_saved = False
    if "workout_type" not in st.session_state:
        st.session_state.workout_type = None
    if "best_frame" not in st.session_state:
        st.session_state.best_frame = None
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏋️ Start Squat Workout"):
            start_workout("squat")
    with col2:
        if st.button("💪 Start Pushup Workout"):
            start_workout("pushup")
    
    if st.session_state.workout_count > 0:
        st.success(f"🏆 Total {st.session_state.workout_type.capitalize()}s: {st.session_state.workout_count}")
        
        if st.button("Save Workout"):
            session_id = save_workout(
                st.session_state.workout_count,
                st.session_state.workout_type.capitalize()
            )
            st.session_state.data_saved = True
            st.write("✅ Workout data saved!")
            
            if st.session_state.best_frame is not None:
                img_path = save_frame(st.session_state.best_frame, session_id)
                st.write("📸 Here is a picture of your exercise workout")
                st.image(img_path, caption="Workout Snapshot", use_container_width=True)
                
if __name__ == "__main__":
    main()
