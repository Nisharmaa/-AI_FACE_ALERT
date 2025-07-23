import cv2
import os
import hashlib
import numpy as np
import face_recognition
import mysql.connector

# ✅ MySQL Connection
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="face_attendance"
    )

# ✅ Face Registration
def register_face(name, email, password):
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    saved_faces = set()
    save_folder = "saved_faces"
    os.makedirs(save_folder, exist_ok=True)

    print("📷 Look at the camera... Press 's' to save, 'q' to exit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 3)
            face = frame[y:y+h, x:x+w]

            face_id = hashlib.md5(face.tobytes()).hexdigest()
            if face_id not in saved_faces:
                face_filename = os.path.join(save_folder, f"face_{len(saved_faces) + 1}.jpg")
                cv2.imwrite(face_filename, face)
                saved_faces.add(face_id)

        cv2.imshow("Face Registration", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and len(faces) > 0:  # Save face when 's' is pressed
            face_encodings = face_recognition.face_encodings(frame)
            if len(face_encodings) > 0:
                face_data = face_encodings[0].tobytes()

                conn = connect_db()
                cursor = conn.cursor()

                try:
                    cursor.execute("INSERT INTO users (name, email, password, face_encoding) VALUES (%s, %s, %s, %s)", 
                                   (name, email, password, face_data))
                    conn.commit()
                    print("✅ Face Registered Successfully!")
                except mysql.connector.Error as err:
                    print(f"❌ Error: {err}")
                finally:
                    conn.close()

        elif key == ord('q') or cv2.getWindowProperty("Face Registration", cv2.WND_PROP_VISIBLE) < 1:
            break

    cap.release()
    cv2.destroyAllWindows()

# ✅ Start Registration
name = input("Enter Name: ")
email = input("Enter Email: ")
password = input("Enter Password: ")

register_face(name, email, password)
