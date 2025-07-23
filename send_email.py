import cv2
import os
import smtplib
import hashlib
from email.message import EmailMessage

# Haarcascade for Face Detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Authorized Faces Folder
authorized_folder = "saved_faces"
unauthorized_folder = "unauthorized_faces"
os.makedirs(unauthorized_folder, exist_ok=True)

# Email Configuration (🔹 Change as needed)
EMAIL_SENDER = "nisha855188@gmail.com"
EMAIL_PASSWORD = "ekkr noho zova cwet"  # 🔹 Generate from Google
EMAIL_RECEIVER = "nisha855188@gmail.com"

# Email Sending Function
def send_email(image_path):
    msg = EmailMessage()
    msg["Subject"] = "🚨 Unauthorized Face Detected!"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("An unknown face was detected. See the attached image.")

    with open(image_path, "rb") as f:
        img_data = f.read()
        msg.add_attachment(img_data, maintype="image", subtype="jpeg", filename="unauthorized.jpg")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
    
    print("📧 Email Alert Sent!")

# Load Authorized Faces
authorized_faces = set()
for filename in os.listdir(authorized_folder):
    path = os.path.join(authorized_folder, filename)
    img = cv2.imread(path, 0)
    if img is not None:
        face_hash = hashlib.md5(img.tobytes()).hexdigest()
        authorized_faces.add(face_hash)

# Start Camera
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        face_hash = hashlib.md5(face.tobytes()).hexdigest()

        if face_hash not in authorized_faces:
            filename = os.path.join(unauthorized_folder, "unauthorized.jpg")
            cv2.imwrite(filename, face)
            print(f"🚨 Unauthorized Face Detected! Saved: {filename}")

            # Send Email Alert
            send_email(filename)

            cap.release()
            cv2.destroyAllWindows()
            exit()

    cv2.imshow("Face Monitoring", frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
