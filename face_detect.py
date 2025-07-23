import cv2

cap = cv2.VideoCapture(0)  # Open camera
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

while cap.isOpened():  # Ensure camera is open
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 3)

    cv2.imshow("Face Detection", frame)

    key = cv2.waitKey(1)  # Super fast response
    if key == ord('q') or cv2.getWindowProperty("Face Detection", cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
