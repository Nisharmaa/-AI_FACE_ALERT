import sys
import os
import csv
import cv2
import numpy as np
import face_recognition
import mysql.connector
import bcrypt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox, QFrame,
    QStackedWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QDateEdit, QFileDialog, QTabWidget, QDialog, QListWidget
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QColor, QPalette
from PyQt6.QtCore import Qt, QSize, QDate
from datetime import datetime, timedelta
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from PyQt6.QtCore import Qt, QSize, QDate, QPropertyAnimation  # Add QPropertyAnimation here
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
from PyQt6.QtWidgets import QGroupBox

# Email settings
EMAIL_SETTINGS = {
    'sender_email': 'nisha855188@gmail.com',
    'sender_password': 'qnhi uciq ugbh fmnn',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587
}

def load_image_safe(path, default_size=(200, 200)):
    """Safe image loading with fallback"""
    try:
        if os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return pixmap.scaled(
                    default_size[0], default_size[1],
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
        # Fallback if image doesn't exist or failed to load
        pixmap = QPixmap(default_size[0], default_size[1])
        pixmap.fill(Qt.GlobalColor.white)
        return pixmap
    except Exception as e:
        print(f"Image loading error: {e}")
        pixmap = QPixmap(default_size[0], default_size[1])
        pixmap.fill(Qt.GlobalColor.gray)
        return pixmap

def connect_db():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="face_attendance"
        )
        if conn.is_connected():
            print("Database connected successfully")
            return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        QMessageBox.critical(None, "Database Error", f"Failed to connect: {e}")
    return None

def create_tables():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS face_attendance")
        cursor.execute("USE face_attendance")
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                face_encoding BLOB,
                role ENUM('student', 'admin') DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                check_in_time DATETIME NOT NULL,
                check_out_time DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id),
                INDEX (user_id, check_in_time)
            )
        """)
        
        # Parents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                email VARCHAR(100) NOT NULL,
                FOREIGN KEY (student_id) REFERENCES users(id),
                UNIQUE (student_id)
            )
        """)
        
        # Add admin user if not exists
        cursor.execute("SELECT * FROM users WHERE email = 'admin@system.com'")
        if not cursor.fetchone():
            hashed_pw = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                ("Admin", "admin@system.com", hashed_pw, "admin")
            )
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4e73df;
                color: white;
                border-radius: 15px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a56c7;
            }
        """)
        self.setFixedHeight(40)

class InputField(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #d1d3e2;
                border-radius: 10px;
                padding: 8px 15px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4e73df;
            }
        """)
        self.setFixedHeight(40)

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Attendance Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

class FaceAttendanceSystem(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Attendance System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set app style
        self.setStyle()
        
        # Create main stack
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create pages
        self.login_page = LoginPage(self)
        self.register_page = RegisterPage(self)
        self.admin_dashboard = None
        self.student_dashboard = None
        
        # Add pages to stack
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)
        
        # Show login page first
        self.stack.setCurrentIndex(0)
    
    def setStyle(self):
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(248, 249, 252))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(53, 58, 64))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #5a5c69;
            }
            QMessageBox {
                background-color: white;
            }
            QTableWidget {
                background-color: white;
                border: 1px solid #d1d3e2;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #4e73df;
                color: white;
                padding: 5px;
                border: none;
            }
        """)
    
    def show_dashboard(self, user_data):
        if user_data['role'] == 'admin':
            if self.admin_dashboard is None:
                self.admin_dashboard = AdminDashboardPage(user_data, self)
                self.stack.addWidget(self.admin_dashboard)
            self.stack.setCurrentWidget(self.admin_dashboard)
        else:
            if self.student_dashboard is None:
                self.student_dashboard = StudentDashboardPage(user_data, self)
                self.stack.addWidget(self.student_dashboard)
            self.stack.setCurrentWidget(self.student_dashboard)
    
    def show_register_page(self):
        self.stack.setCurrentWidget(self.register_page)
    
    def show_login_page(self):
        self.stack.setCurrentWidget(self.login_page)

class LoginPage(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Left side (graphics)
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: #4e73df; border-radius: 15px;")
        left_layout = QVBoxLayout(left_frame)
        
        # Logo and title
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(load_image_safe("assets/logo.png"))
        
        title = QLabel("Smart Attendance System")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addStretch()
        left_layout.addWidget(logo)
        left_layout.addWidget(title)
        left_layout.addStretch()
        
        # Right side (form)
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: white; border-radius: 15px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(40, 40, 40, 40)
        
        # Form title
        form_title = QLabel("Login to Your Account")
        form_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4e73df;")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Input fields
        self.email_input = InputField("Email Address")
        self.password_input = InputField("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Buttons
        login_btn = RoundedButton("Login with Credentials")
        login_btn.clicked.connect(self.handle_login)
        
        face_login_btn = RoundedButton("Login with Face Recognition")
        face_login_btn.setIcon(QIcon("assets/face_id.png"))
        face_login_btn.setIconSize(QSize(20, 20))
        face_login_btn.clicked.connect(self.handle_face_login)
        
        register_btn = QPushButton("Don't have an account? Register")
        register_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #4e73df;
                font-size: 12px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        register_btn.clicked.connect(self.parent.show_register_page)
        
        # Add widgets to right layout
        right_layout.addWidget(form_title)
        right_layout.addSpacing(30)
        right_layout.addWidget(QLabel("Email:"))
        right_layout.addWidget(self.email_input)
        right_layout.addSpacing(15)
        right_layout.addWidget(QLabel("Password:"))
        right_layout.addWidget(self.password_input)
        right_layout.addSpacing(30)
        right_layout.addWidget(login_btn)
        right_layout.addSpacing(15)
        right_layout.addWidget(face_login_btn)
        right_layout.addSpacing(30)
        right_layout.addWidget(register_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add frames to main layout
        layout.addWidget(left_frame, stretch=1)
        layout.addWidget(right_frame, stretch=1)
    
    def handle_login(self):
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Error", "Please enter both email and password")
            return
            
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, email, password, role FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                if bcrypt.checkpw(password.encode(), user['password'].encode()):
                    self.parent.show_dashboard({
                        'id': user['id'],
                        'name': user['name'],
                        'email': user['email'],
                        'role': user['role']
                    })
                else:
                    QMessageBox.critical(self, "Error", "Incorrect password")
            else:
                QMessageBox.critical(self, "Error", "User not found")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def handle_face_login(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            QMessageBox.critical(self, "Error", "Could not access camera")
            return
            
        try:
            conn = connect_db()
            if not conn:
                return
                
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, email, face_encoding, role FROM users")
            users = cursor.fetchall()
            
            if not users:
                QMessageBox.warning(self, "Error", "No registered users found")
                return
                
            known_face_encodings = []
            known_face_data = []
            
            for user in users:
                if user['face_encoding']:
                    try:
                        face_encoding = np.frombuffer(user['face_encoding'], dtype=np.float64)
                        known_face_encodings.append(face_encoding)
                        known_face_data.append({
                            'id': user['id'],
                            'name': user['name'],
                            'email': user['email'],
                            'role': user['role']
                        })
                    except Exception as e:
                        print(f"Error loading face encoding for user {user['id']}: {e}")
                        continue
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    QMessageBox.critical(self, "Error", "Failed to capture frame")
                    break
                
                # Convert frame to RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Find face locations
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if face_locations:
                    # Get face encodings
                    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                    
                    for face_encoding in face_encodings:
                        # Use lower tolerance for more strict matching
                        matches = face_recognition.compare_faces(
                            known_face_encodings, 
                            face_encoding, 
                            tolerance=0.5  # Lower is more strict (default is 0.6)
                        )
                        
                        # Get all matches instead of just the first one
                        matched_users = [
                            user for user, match in zip(known_face_data, matches) 
                            if match
                        ]
                        
                        if len(matched_users) == 1:
                            self.parent.show_dashboard(matched_users[0])
                            return
                        elif len(matched_users) > 1:
                            # If multiple matches, let user choose
                            self.show_user_selection_dialog(matched_users)
                            return
                
                # Show camera feed
                cv2.imshow("Face Login", frame)
                if cv2.waitKey(1) == 27:  # ESC key
                    break
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Face recognition failed: {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals() and conn.is_connected():
                conn.close()
            cap.release()
            cv2.destroyAllWindows()
    
    def show_user_selection_dialog(self, users):
        dialog = QDialog(self)
        dialog.setWindowTitle("Multiple Accounts Found")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        label = QLabel("Your face matches multiple accounts. Please select:")
        layout.addWidget(label)
        
        self.user_list = QListWidget()
        for user in users:
            self.user_list.addItem(f"{user['name']} ({user['email']})")
        layout.addWidget(self.user_list)
        
        btn = QPushButton("Login")
        btn.clicked.connect(lambda: self.on_user_selected(users, dialog))
        layout.addWidget(btn)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def on_user_selected(self, users, dialog):
        selected = self.user_list.currentRow()
        if selected >= 0:
            self.parent.show_dashboard(users[selected])
            dialog.close()

# Register Page
class RegisterPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Left side (graphics)
        left_frame = QFrame()
        left_frame.setStyleSheet("background-color: #4e73df; border-radius: 15px;")
        left_layout = QVBoxLayout(left_frame)
        
        # Logo and title
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setPixmap(QPixmap("assets/register.png").scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
        
        title = QLabel("Create Your Account")
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addStretch()
        left_layout.addWidget(logo)
        left_layout.addWidget(title)
        left_layout.addStretch()
        
        # Right side (form)
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: white; border-radius: 15px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(40, 40, 40, 40)
        
        # Form title
        form_title = QLabel("Register New User")
        form_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4e73df;")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Input fields
        self.name_input = InputField("👤 Full Name")
        self.email_input = InputField("📧 Email Address")
        self.password_input = InputField("🔑 Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Buttons
        register_btn = RoundedButton("Register Face")
        register_btn.setIcon(QIcon("assets/face_id.png"))
        register_btn.setIconSize(QSize(20, 20))
        register_btn.clicked.connect(self.handle_register)
        
        login_btn = QPushButton("Already have an account? Login")
        login_btn.setStyleSheet("""
            QPushButton {
                border: none;
                color: #4e73df;
                font-size: 12px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        login_btn.clicked.connect(self.parent.show_login_page)
        
        # Add widgets to right layout
        right_layout.addWidget(form_title)
        right_layout.addSpacing(30)
        right_layout.addWidget(QLabel("Full Name:"))
        right_layout.addWidget(self.name_input)
        right_layout.addSpacing(15)
        right_layout.addWidget(QLabel("Email:"))
        right_layout.addWidget(self.email_input)
        right_layout.addSpacing(15)
        right_layout.addWidget(QLabel("Password:"))
        right_layout.addWidget(self.password_input)
        right_layout.addSpacing(30)
        right_layout.addWidget(register_btn)
        right_layout.addSpacing(30)
        right_layout.addWidget(login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Add frames to main layout
        layout.addWidget(left_frame, stretch=1)
        layout.addWidget(right_frame, stretch=1)
    
    def handle_register(self):
        name = self.name_input.text()
        email = self.email_input.text()
        password = self.password_input.text()
        
        if not all([name, email, password]):
            QMessageBox.warning(self, "Error", "All fields are required")
            return
            
        # Validate email format
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
            
        # Validate password strength
        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return
            
        # Capture face
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            QMessageBox.critical(self, "Error", "Could not access camera")
            return
            
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    QMessageBox.critical(self, "Error", "Failed to capture frame")
                    break
                
                # Display instructions
                cv2.putText(frame, "Look at the camera and blink", (20, 40), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, "Press SPACE to capture", (20, 80), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, "Press ESC to cancel", (20, 120), 
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                cv2.imshow("Face Registration", frame)
                
                key = cv2.waitKey(1)
                if key == 32:  # SPACE
                    # Detect liveness (simple blink detection)
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
                    eyes = eye_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
                    
                    if len(eyes) < 2:
                        QMessageBox.warning(self, "Error", "Please blink to prove liveness")
                        continue
                        
                    # Get face encoding
                    face_encodings = face_recognition.face_encodings(frame)
                    if not face_encodings:
                        QMessageBox.warning(self, "Error", "No face detected")
                        continue
                    
                    face_encoding = face_encodings[0]
                    
                    # Check if face already exists in database
                    conn = connect_db()
                    if not conn:
                        return
                        
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT id, name, face_encoding FROM users WHERE face_encoding IS NOT NULL")
                    existing_users = cursor.fetchall()
                    
                    for user in existing_users:
                        if user['face_encoding']:
                            stored_encoding = np.frombuffer(user['face_encoding'], dtype=np.float64)
                            match = face_recognition.compare_faces([stored_encoding], face_encoding, tolerance=0.5)
                            if match[0]:
                                QMessageBox.warning(
                                    self, 
                                    "Face Already Registered", 
                                    f"This face is already registered as {user['name']}!\n"
                                    "Each face can only be registered to one account."
                                )
                                return
                    
                    # Hash password
                    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    
                    # Save to database
                    try:
                        cursor.execute(
                            "INSERT INTO users (name, email, password, face_encoding) VALUES (%s, %s, %s, %s)",
                            (name, email, hashed_pw, face_encoding.tobytes())
                        )
                        conn.commit()
                        QMessageBox.information(self, "Success", "Registration successful!")
                        self.parent.show_login_page()
                        break
                    except mysql.connector.IntegrityError:
                        QMessageBox.critical(self, "Error", "Email already registered")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Registration failed: {e}")
                    finally:
                        if conn.is_connected():
                            cursor.close()
                            conn.close()
                elif key == 27:  # ESC
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

# Student Dashboard
class StudentDashboardPage(QWidget):
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.parent_app = parent  # Store reference to main app
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QWidget()
        header.setStyleSheet("background-color: white; border-radius: 15px;")
        header_layout = QHBoxLayout(header)
        
        # User info
        user_info = QLabel(f"""
            <h2 style="color: #4e73df;">Welcome, {self.user_data['name']}!</h2>
            <p>Email: {self.user_data['email']}</p>
            <p>Last login: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        """)
        user_info.setFont(QFont("Arial", 12))
        
        # Profile picture placeholder
        profile_pic = QLabel()
        profile_pic.setPixmap(QPixmap("assets/profile.png").scaled(80, 80))
        profile_pic.setStyleSheet("border: 2px solid #4e73df; border-radius: 40px;")
        
        header_layout.addWidget(user_info)
        header_layout.addWidget(profile_pic)
        
        # Attendance section
        attendance_frame = QFrame()
        attendance_frame.setStyleSheet("background-color: white; border-radius: 15px;")
        attendance_layout = QVBoxLayout(attendance_frame)
        
        attendance_title = QLabel("Attendance")
        attendance_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4e73df;")
        
        self.attendance_btn = RoundedButton("Mark Attendance")
        self.attendance_btn.clicked.connect(self.mark_attendance)
        
        self.attendance_status = QLabel("Status: Not checked in today")
        self.attendance_status.setStyleSheet("font-size: 14px;")
        
        # Attendance history table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(3)
        self.attendance_table.setHorizontalHeaderLabels(["Date", "Check In", "Check Out"])
        self.attendance_table.horizontalHeader().setStretchLastSection(True)
        self.attendance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        attendance_layout.addWidget(attendance_title)
        attendance_layout.addSpacing(20)
        attendance_layout.addWidget(self.attendance_btn)
        attendance_layout.addSpacing(20)
        attendance_layout.addWidget(self.attendance_status)
        attendance_layout.addSpacing(20)
        attendance_layout.addWidget(self.attendance_table)
        
        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                color: #e74a3b;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        
        # Add widgets to main layout
        layout.addWidget(header)
        layout.addSpacing(20)
        layout.addWidget(attendance_frame)
        layout.addStretch()
        layout.addWidget(logout_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Load initial data
        self.load_attendance_status()
        self.load_attendance_history()
    
    def load_attendance_status(self):
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT check_in_time, check_out_time 
                FROM attendance 
                WHERE user_id = %s AND DATE(check_in_time) = CURDATE()
                ORDER BY check_in_time DESC 
                LIMIT 1
            """, (self.user_data['id'],))
            
            result = cursor.fetchone()
            if result:
                check_in, check_out = result
                status = f"Checked in: {check_in.strftime('%H:%M')}"
                if check_out:
                    status += f" | Checked out: {check_out.strftime('%H:%M')}"
                    self.attendance_btn.setText("Mark Attendance")
                else:
                    status += " | Still checked in"
                    self.attendance_btn.setText("Check Out")
                self.attendance_status.setText(status)
            else:
                self.attendance_status.setText("Status: Not checked in today")
                self.attendance_btn.setText("Mark Attendance")
        except Exception as e:
            print(f"Error loading attendance: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def load_attendance_history(self):
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DATE(check_in_time) as date, 
                       TIME(check_in_time) as check_in, 
                       TIME(check_out_time) as check_out
                FROM attendance 
                WHERE user_id = %s
                ORDER BY date DESC
                LIMIT 30
            """, (self.user_data['id'],))
            
            records = cursor.fetchall()
            self.attendance_table.setRowCount(len(records))
            
            for row_idx, (date, check_in, check_out) in enumerate(records):
                self.attendance_table.setItem(row_idx, 0, QTableWidgetItem(str(date)))
                self.attendance_table.setItem(row_idx, 1, QTableWidgetItem(str(check_in) if check_in else ""))
                self.attendance_table.setItem(row_idx, 2, QTableWidgetItem(str(check_out) if check_out else ""))
                
        except Exception as e:
            print(f"Error loading attendance history: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def mark_attendance(self):
        conn = connect_db()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, check_out_time FROM attendance 
                WHERE user_id = %s AND DATE(check_in_time) = CURDATE()
                ORDER BY check_in_time DESC LIMIT 1
            """, (self.user_data['id'],))
            
            record = cursor.fetchone()
            
            if record and record[1] is None:  # Check-out
                cursor.execute("UPDATE attendance SET check_out_time = %s WHERE id = %s", 
                             (datetime.now(), record[0]))
                status = "checked out"
            else:  # Check-in
                cursor.execute("INSERT INTO attendance (user_id, check_in_time) VALUES (%s, %s)", 
                             (self.user_data['id'], datetime.now()))
                status = "checked in"
            
            conn.commit()
            
            # Send email notification
            self.send_attendance_email(status)
            
            QMessageBox.information(
                self, 
                "Success", 
                f"Attendance marked! {status.capitalize()} at {datetime.now().strftime('%H:%M')}"
            )
            
            # Refresh display
            self.load_attendance_status()
            self.load_attendance_history()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to mark attendance: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def send_attendance_email(self, status):
        """Send email when attendance is marked"""
        try:
            conn = connect_db()
            cursor = conn.cursor(dictionary=True)
            
            # Get parent email
            cursor.execute("""
                SELECT email FROM parents WHERE student_id = %s
            """, (self.user_data['id'],))
            result = cursor.fetchone()
            
            if not result or not result.get('email'):
                print("No parent email registered for this student")
                return
            
            parent_email = result['email']
            
            # Email content
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SETTINGS['sender_email']
            msg['To'] = parent_email
            msg['Subject'] = f"Attendance Update for {self.user_data['name']}"
            
            body = f"""
            Attendance Notification:
            
            Student: {self.user_data['name']}
            Status: {status.capitalize()}
            Time: {datetime.now().strftime('%I:%M %p')}
            Date: {datetime.now().strftime('%B %d, %Y')}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(EMAIL_SETTINGS['smtp_server'], EMAIL_SETTINGS['smtp_port']) as server:
                server.starttls()
                server.login(EMAIL_SETTINGS['sender_email'], EMAIL_SETTINGS['sender_password'])
                server.send_message(msg)
                
        except Exception as e:
            print(f"Email notification failed: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    
    def logout(self):
        self.parent_app.show_login_page()

# Admin Dashboard
class AdminDashboardPage(QWidget):
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.parent_app = parent
        self.camera_active = False
        self.cap = None
        self.setup_ui()
        
        # Add fade-in animation
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

    def setup_ui(self):
        self.setStyleSheet("background: #f8f9fc;")
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)
        
        # Header with user profile
        header = QFrame()
        header.setStyleSheet("""
            background: white;
            border-radius: 12px;
            padding: 20px;
        """)
        
        header_layout = QHBoxLayout(header)
        
        # Welcome message
        welcome_msg = QLabel(f"""
            <h2 style="color: #4e73df; margin-bottom: 5px;">Admin Dashboard</h2>
            <p style="color: #858796; margin-top: 0;">Welcome back, <b>{self.user_data['name']}</b></p>
        """)
        
        # User profile with avatar
        profile_section = QHBoxLayout()
        
        avatar = QLabel()
        if os.path.exists("assets/admin.png"):
            avatar.setPixmap(load_image_safe("assets/admin.png", (60, 60)))
        else:
            avatar.setText(self.user_data['name'][0].upper())
            avatar.setStyleSheet("""
                background: #4e73df;
                color: white;
                border-radius: 30px;
                font-size: 24px;
                font-weight: bold;
                qproperty-alignment: AlignCenter;
            """)
            avatar.setFixedSize(60, 60)
        
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                color: #e74a3b;
                font-size: 13px;
                border: 1px solid #e74a3b;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: #f8d7da;
            }
        """)
        logout_btn.clicked.connect(self.logout)
        
        profile_section.addWidget(avatar)
        profile_section.addSpacing(10)
        profile_section.addWidget(logout_btn)
        profile_section.addStretch()
        
        header_layout.addWidget(welcome_msg)
        header_layout.addStretch()
        header_layout.addLayout(profile_section)
        
        # Stats cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)
        
        # Card 1 - Total Users
        users_card = self.create_stat_card(
            "Total Users", 
            str(self.get_user_count()), 
            "#4e73df", 
            "assets/users_icon.png"
        )
        
        # Card 2 - Today's Attendance
        attendance_card = self.create_stat_card(
            "Today's Attendance", 
            f"{self.get_todays_attendance()}%", 
            "#1cc88a", 
            "assets/attendance_icon.png"
        )
        
        # Card 3 - Pending Actions
        pending_card = self.create_stat_card(
            "Pending Actions", 
            str(self.get_pending_actions()), 
            "#f6c23e", 
            "assets/pending_icon.png"
        )
        
        stats_row.addWidget(users_card)
        stats_row.addWidget(attendance_card)
        stats_row.addWidget(pending_card)
        
        # Main content tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            
            QTabBar::tab:selected {
                background: white;
                color: #4e73df;
                border-bottom: 2px solid #4e73df;
            }
            
            QTabBar::tab:!selected {
                background: #f8f9fc;
                color: #858796;
            }
        """)
        
        # Add tabs
        self.tabs.addTab(self.create_users_tab(), "Users")
        self.tabs.addTab(self.create_attendance_tab(), "Attendance")
        self.tabs.addTab(self.create_multi_attendance_tab(), "Bulk Check-in")
        self.tabs.addTab(self.create_parent_email_tab(), "Parent Emails")
        
        # Add widgets to main layout
        main_layout.addWidget(header)
        main_layout.addLayout(stats_row)
        main_layout.addWidget(self.tabs)

    def logout(self):
        if self.camera_active:
            self.toggle_camera()  # Turn off camera if active
        self.parent_app.show_login_page()

    def create_stat_card(self, title, value, color, icon_path):
        """Create a statistic card widget"""
        card = QFrame()
        card.setStyleSheet(f"""
            background: white;
            border-left: 4px solid {color};
            border-radius: 8px;
            padding: 15px;
        """)
        
        layout = QHBoxLayout(card)
        
        # Icon
        icon = QLabel()
        if os.path.exists(icon_path):
            icon.setPixmap(load_image_safe(icon_path, (40, 40)))
        else:
            icon.setText("")
            icon.setFixedSize(40, 40)
        layout.addWidget(icon)
        
        # Text
        text_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #858796; font-size: 12px;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(value_label)
        layout.addLayout(text_layout)
        
        return card

    def get_user_count(self):
        """Get total number of users"""
        conn = connect_db()
        if not conn:
            return 0
            
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
        except:
            return 0
        finally:
            if conn.is_connected():
                conn.close()

    def get_todays_attendance(self):
        """Get today's attendance percentage"""
        conn = connect_db()
        if not conn:
            return 0
            
        try:
            cursor = conn.cursor()
            # Get total students
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'student'")
            total_students = cursor.fetchone()[0] or 1  # Avoid division by zero
            
            # Get students who checked in today
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) 
                FROM attendance 
                WHERE DATE(check_in_time) = CURDATE()
            """)
            attended = cursor.fetchone()[0]
            
            return round((attended / total_students) * 100)
        except:
            return 0
        finally:
            if conn.is_connected():
                conn.close()

    def get_pending_actions(self):
        """Get number of pending actions (placeholder)"""
        return 0

    def create_users_tab(self):
        """Create the users management tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Add user button
        add_btn = QPushButton("Add New User")
        add_btn.setStyleSheet("""
            QPushButton {
                background: #4e73df;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        add_btn.clicked.connect(self.show_add_user_dialog)
        
        # Search and filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search:"))
        
        self.user_search = QLineEdit()
        self.user_search.setPlaceholderText("Search by name or email")
        self.user_search.textChanged.connect(self.load_users)
        filter_layout.addWidget(self.user_search)
        
        # Users table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels(["ID", "Name", "Email", "Role", "Actions"])
        self.users_table.horizontalHeader().setStretchLastSection(True)
        self.users_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Add widgets
        layout.addWidget(add_btn)
        layout.addLayout(filter_layout)
        layout.addWidget(self.users_table)
        
        # Load initial data
        self.load_users()
        
        return tab

    def show_add_user_dialog(self):
        """Show dialog to add new user"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New User")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Name:"))
        name_edit = QLineEdit()
        name_layout.addWidget(name_edit)
        
        # Email field
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Email:"))
        email_edit = QLineEdit()
        email_layout.addWidget(email_edit)
        
        # Password field
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("Password:"))
        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        pass_layout.addWidget(pass_edit)
        
        # Role field
        role_layout = QHBoxLayout()
        role_layout.addWidget(QLabel("Role:"))
        role_combo = QComboBox()
        role_combo.addItems(["student", "admin"])
        role_layout.addWidget(role_combo)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_new_user(
            name_edit.text(), email_edit.text(), pass_edit.text(), role_combo.currentText(), dialog
        ))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        # Add to layout
        layout.addLayout(name_layout)
        layout.addLayout(email_layout)
        layout.addLayout(pass_layout)
        layout.addLayout(role_layout)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def save_new_user(self, name, email, password, role, dialog):
        """Save a new user to database"""
        if not all([name, email, password]):
            QMessageBox.warning(self, "Error", "All fields are required")
            return
            
        if "@" not in email or "." not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters")
            return
            
        conn = connect_db()
        try:
            cursor = conn.cursor()
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            
            cursor.execute(
                "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                (name, email, hashed_pw, role)
            )
            conn.commit()
            QMessageBox.information(self, "Success", "User added successfully")
            dialog.accept()
            self.load_users()  # Refresh user list
        except mysql.connector.IntegrityError:
            QMessageBox.warning(self, "Error", "Email already exists")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add user: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def load_users(self):
        """Load users into the table"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            search_term = self.user_search.text()
            
            query = "SELECT id, name, email, role FROM users"
            params = []
            
            if search_term:
                query += " WHERE name LIKE %s OR email LIKE %s"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            cursor.execute(query, params)
            users = cursor.fetchall()
            
            self.users_table.setRowCount(len(users))
            
            for row_idx, user in enumerate(users):
                self.users_table.setItem(row_idx, 0, QTableWidgetItem(str(user['id'])))
                self.users_table.setItem(row_idx, 1, QTableWidgetItem(user['name']))
                self.users_table.setItem(row_idx, 2, QTableWidgetItem(user['email']))
                self.users_table.setItem(row_idx, 3, QTableWidgetItem(user['role']))
                
                # Action buttons
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                
                edit_btn = QPushButton("Edit")
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background: #4e73df;
                        color: white;
                        border-radius: 4px;
                        padding: 5px;
                    }
                """)
                edit_btn.clicked.connect(lambda _, uid=user['id']: self.edit_user(uid))
                
                delete_btn = QPushButton("Delete")
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background: #e74a3b;
                        color: white;
                        border-radius: 4px;
                        padding: 5px;
                    }
                """)
                delete_btn.clicked.connect(lambda _, uid=user['id']: self.delete_user(uid))
                
                btn_layout.addWidget(edit_btn)
                btn_layout.addWidget(delete_btn)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                
                self.users_table.setCellWidget(row_idx, 4, btn_widget)
                
        except Exception as e:
            print(f"Error loading users: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def edit_user(self, user_id):
        """Edit user details dialog"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, name, email, role FROM users WHERE id = %s", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                QMessageBox.warning(self, "Error", "User not found")
                return
                
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit User")
            dialog.setFixedSize(400, 300)
            
            layout = QVBoxLayout(dialog)
            
            # Name field
            name_layout = QHBoxLayout()
            name_layout.addWidget(QLabel("Name:"))
            name_edit = QLineEdit(user['name'])
            name_layout.addWidget(name_edit)
            
            # Email field
            email_layout = QHBoxLayout()
            email_layout.addWidget(QLabel("Email:"))
            email_edit = QLineEdit(user['email'])
            email_layout.addWidget(email_edit)
            
            # Role field
            role_layout = QHBoxLayout()
            role_layout.addWidget(QLabel("Role:"))
            role_combo = QComboBox()
            role_combo.addItems(["student", "admin"])
            role_combo.setCurrentText(user['role'])
            role_layout.addWidget(role_combo)
            
            # Buttons
            btn_layout = QHBoxLayout()
            save_btn = QPushButton("Save")
            save_btn.clicked.connect(lambda: self.save_user_edits(
                user_id, name_edit.text(), email_edit.text(), role_combo.currentText(), dialog
            ))
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            
            btn_layout.addWidget(save_btn)
            btn_layout.addWidget(cancel_btn)
            
            # Add to layout
            layout.addLayout(name_layout)
            layout.addLayout(email_layout)
            layout.addLayout(role_layout)
            layout.addLayout(btn_layout)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit user: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def save_user_edits(self, user_id, name, email, role, dialog):
        """Save edited user details"""
        if not name or not email:
            QMessageBox.warning(self, "Error", "Name and email are required")
            return
            
        conn = connect_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET name = %s, email = %s, role = %s WHERE id = %s",
                (name, email, role, user_id)
            )
            conn.commit()
            QMessageBox.information(self, "Success", "User updated successfully")
            dialog.accept()
            self.load_users()  # Refresh the user list
        except mysql.connector.IntegrityError:
            QMessageBox.warning(self, "Error", "Email already exists")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update user: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def delete_user(self, user_id):
        """Delete a user"""
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            "Are you sure you want to delete this user?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            conn = connect_db()
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {e}")
            finally:
                if conn.is_connected():
                    conn.close()

    def create_attendance_tab(self):
        """Create the attendance records tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Date filter
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("From:"))
        
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-7))
        self.from_date.setCalendarPopup(True)
        date_layout.addWidget(self.from_date)
        
        date_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setCalendarPopup(True)
        date_layout.addWidget(self.to_date)
        
        filter_btn = QPushButton("Filter")
        filter_btn.setStyleSheet("""
            QPushButton {
                background: #4e73df;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        filter_btn.clicked.connect(self.load_attendance)
        date_layout.addWidget(filter_btn)
        
        # Export button
        export_btn = QPushButton("Export to PDF")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #1cc88a;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        export_btn.clicked.connect(self.export_attendance_pdf)
        date_layout.addWidget(export_btn)
        
        # Attendance table
        self.attendance_table = QTableWidget()
        self.attendance_table.setColumnCount(5)
        self.attendance_table.setHorizontalHeaderLabels(["ID", "Name", "Date", "Check In", "Check Out"])
        self.attendance_table.horizontalHeader().setStretchLastSection(True)
        self.attendance_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Add widgets
        layout.addLayout(date_layout)
        layout.addWidget(self.attendance_table)
        
        # Load initial data
        self.load_attendance()
        
        return tab

    def load_attendance(self):
        """Load attendance records"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            from_date = self.from_date.date().toString("yyyy-MM-dd")
            to_date = self.to_date.date().toString("yyyy-MM-dd")
            
            cursor.execute("""
                SELECT a.id, u.name, DATE(a.check_in_time) as date, 
                       TIME(a.check_in_time) as check_in, 
                       TIME(a.check_out_time) as check_out
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                WHERE DATE(a.check_in_time) BETWEEN %s AND %s
                ORDER BY date DESC, check_in DESC
            """, (from_date, to_date))
            
            records = cursor.fetchall()
            self.attendance_table.setRowCount(len(records))
            
            for row_idx, record in enumerate(records):
                self.attendance_table.setItem(row_idx, 0, QTableWidgetItem(str(record['id'])))
                self.attendance_table.setItem(row_idx, 1, QTableWidgetItem(record['name']))
                self.attendance_table.setItem(row_idx, 2, QTableWidgetItem(str(record['date'])))
                self.attendance_table.setItem(row_idx, 3, QTableWidgetItem(str(record['check_in'])))
                self.attendance_table.setItem(row_idx, 4, QTableWidgetItem(str(record['check_out']) if record['check_out'] else ""))
                
        except Exception as e:
            print(f"Error loading attendance: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def export_attendance_pdf(self):
        """Export attendance records to PDF"""
        from_date = self.from_date.date().toString("yyyy-MM-dd")
        to_date = self.to_date.date().toString("yyyy-MM-dd")
        
        # Get data from database
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.name, DATE(a.check_in_time) as date, 
                       TIME(a.check_in_time) as check_in, 
                       TIME(a.check_out_time) as check_out
                FROM attendance a
                JOIN users u ON a.user_id = u.id
                WHERE DATE(a.check_in_time) BETWEEN %s AND %s
                ORDER BY date DESC, check_in DESC
            """, (from_date, to_date))
            
            records = cursor.fetchall()
            
            if not records:
                QMessageBox.warning(self, "Warning", "No attendance records to export")
                return
                
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Title
            pdf.cell(200, 10, txt="Attendance Report", ln=1, align='C')
            pdf.cell(200, 10, txt=f"From {from_date} to {to_date}", ln=1, align='C')
            pdf.ln(10)
            
            # Table header
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(60, 10, "Name", border=1)
            pdf.cell(40, 10, "Date", border=1)
            pdf.cell(40, 10, "Check In", border=1)
            pdf.cell(40, 10, "Check Out", border=1)
            pdf.ln()
            
            # Table rows
            pdf.set_font("Arial", size=10)
            for record in records:
                pdf.cell(60, 10, record['name'], border=1)
                pdf.cell(40, 10, str(record['date']), border=1)
                pdf.cell(40, 10, str(record['check_in']), border=1)
                pdf.cell(40, 10, str(record['check_out']) if record['check_out'] else "", border=1)
                pdf.ln()
            
            # Save file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF Report", "", "PDF Files (*.pdf)"
            )
            
            if file_path:
                if not file_path.endswith('.pdf'):
                    file_path += '.pdf'
                pdf.output(file_path)
                QMessageBox.information(self, "Success", "PDF report exported successfully")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export PDF: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def create_multi_attendance_tab(self):
        """Create tab for bulk attendance marking"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Instructions
        instructions = QLabel("""
            <h3>Bulk Attendance Check-in</h3>
            <p>Use this feature to mark attendance for multiple students at once.</p>
            <p>1. Click 'Start Camera' to begin face detection</p>
            <p>2. Detected students will be automatically checked in</p>
        """)
        
        # Camera controls
        camera_layout = QHBoxLayout()
        self.camera_btn = QPushButton("Start Camera")
        self.camera_btn.setStyleSheet("""
            QPushButton {
                background: #4e73df;
                color: white;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        self.camera_btn.clicked.connect(self.toggle_camera)
        camera_layout.addWidget(self.camera_btn)
        
        # Status label
        self.camera_status = QLabel("Camera: Off")
        
        # Detected students list
        self.detected_list = QListWidget()
        
        # Add widgets
        layout.addWidget(instructions)
        layout.addLayout(camera_layout)
        layout.addWidget(self.camera_status)
        layout.addWidget(self.detected_list)
        
        return tab

    def toggle_camera(self):
        """Toggle camera for bulk attendance"""
        if self.camera_active:
            # Stop camera
            self.camera_active = False
            self.camera_btn.setText("Start Camera")
            self.camera_status.setText("Camera: Off")
            if self.cap:
                self.cap.release()
                cv2.destroyAllWindows()
        else:
            # Start camera
            self.camera_active = True
            self.camera_btn.setText("Stop Camera")
            self.camera_status.setText("Camera: On - Detecting faces...")
            self.detected_list.clear()
            
            # Load known face encodings
            known_face_encodings = []
            known_face_names = []
            known_face_ids = []
            
            conn = connect_db()
            if not conn:
                self.toggle_camera()  # Turn off if DB fails
                return
                
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, name, face_encoding FROM users WHERE face_encoding IS NOT NULL")
                users = cursor.fetchall()
                
                for user in users:
                    try:
                        face_encoding = np.frombuffer(user['face_encoding'], dtype=np.float64)
                        known_face_encodings.append(face_encoding)
                        known_face_names.append(user['name'])
                        known_face_ids.append(user['id'])
                    except Exception as e:
                        print(f"Error loading face for {user['name']}: {e}")
                        
                if not known_face_encodings:
                    QMessageBox.warning(self, "Warning", "No registered faces found in database")
                    self.toggle_camera()  # Turn off if no faces
                    return
                    
                # Start video capture
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    QMessageBox.critical(self, "Error", "Could not access camera")
                    self.toggle_camera()  # Turn off if camera fails
                    return
                    
                # Process frames
                while self.camera_active:
                    ret, frame = self.cap.read()
                    if not ret:
                        break
                        
                    # Resize frame for faster processing
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    
                    # Find all face locations and encodings
                    face_locations = face_recognition.face_locations(rgb_small_frame)
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                    
                    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                        # Scale back up face locations
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4
                        
                        # Compare with known faces
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                        name = "Unknown"
                        user_id = None
                        
                        # Use the known face with the smallest distance to the new face
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = known_face_names[best_match_index]
                            user_id = known_face_ids[best_match_index]
                            
                            # Mark attendance if not already marked today
                            if not self.is_checked_in_today(user_id):
                                self.mark_attendance(user_id)
                                self.detected_list.addItem(f"{name} - Checked in at {datetime.now().strftime('%H:%M')}")
                                
                        # Draw box and label
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
                        cv2.putText(frame, name, (left + 6, bottom - 6), 
                                   cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)
                    
                    # Display the resulting image
                    cv2.imshow('Bulk Attendance Check-in', frame)
                    
                    # Break loop if 'q' is pressed
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                        
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Face detection failed: {e}")
            finally:
                if conn.is_connected():
                    conn.close()
                if self.camera_active:
                    self.toggle_camera()  # Ensure cleanup if we exited unexpectedly
                cv2.destroyAllWindows()

    def is_checked_in_today(self, user_id):
        """Check if user already checked in today"""
        conn = connect_db()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM attendance 
                WHERE user_id = %s AND DATE(check_in_time) = CURDATE()
                LIMIT 1
            """, (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking attendance: {e}")
            return True  # Assume checked in to prevent duplicates
        finally:
            if conn.is_connected():
                conn.close()

    def mark_attendance(self, user_id):
        """Mark attendance for a user"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO attendance (user_id, check_in_time) VALUES (%s, %s)",
                (user_id, datetime.now())
            )
            conn.commit()
        except Exception as e:
            print(f"Error marking attendance: {e}")
        finally:
            if conn.is_connected():
                conn.close()

    def create_parent_email_tab(self):
        """Create a comprehensive tab for managing parent emails"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Section 1: Add/Edit Parent Email
        group_box = QGroupBox("Set Parent Email for Student")
        group_layout = QVBoxLayout(group_box)
        
        # Student selection
        student_layout = QHBoxLayout()
        student_layout.addWidget(QLabel("Select Student:"))
        
        self.student_combo = QComboBox()
        self.load_student_combo()
        student_layout.addWidget(self.student_combo)
        
        # Parent email input
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Parent Email:"))
        
        self.parent_email_input = QLineEdit()
        self.parent_email_input.setPlaceholderText("parent@example.com")
        
        # Set up email validator
        email_regex = QRegularExpression(r"[^@]+@[^@]+\.[^@]+")
        email_validator = QRegularExpressionValidator(email_regex, self.parent_email_input)
        self.parent_email_input.setValidator(email_validator)
        
        email_layout.addWidget(self.parent_email_input)
        
        # Current email display
        self.current_email_label = QLabel("Current parent email: None")
        self.current_email_label.setStyleSheet("font-style: italic;")
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = RoundedButton("Save Email")
        save_btn.clicked.connect(self.save_parent_email)
        btn_layout.addWidget(save_btn)
        
        # Add to group box
        group_layout.addLayout(student_layout)
        group_layout.addLayout(email_layout)
        group_layout.addWidget(self.current_email_label)
        group_layout.addLayout(btn_layout)
        
        # Section 2: View All Parent Emails
        view_group = QGroupBox("All Parent Emails")
        view_layout = QVBoxLayout(view_group)
        
        # Search functionality
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.parent_search = QLineEdit()
        self.parent_search.setPlaceholderText("Search by student or parent email")
        self.parent_search.textChanged.connect(self.load_parent_emails)
        search_layout.addWidget(self.parent_search)
        
        # Parent emails table
        self.parent_emails_table = QTableWidget()
        self.parent_emails_table.setColumnCount(3)
        self.parent_emails_table.setHorizontalHeaderLabels(["Student ID", "Student Name", "Parent Email"])
        self.parent_emails_table.horizontalHeader().setStretchLastSection(True)
        self.parent_emails_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Add to view group
        view_layout.addLayout(search_layout)
        view_layout.addWidget(self.parent_emails_table)
        
        # Export button
        export_btn = RoundedButton("Export to CSV")
        export_btn.clicked.connect(self.export_parent_emails_csv)
        
        # Add sections to main layout
        layout.addWidget(group_box)
        layout.addWidget(view_group)
        layout.addWidget(export_btn)
        
        # Load initial data
        self.load_current_parent_email()
        self.load_parent_emails()
        
        # Connect student selection change
        self.student_combo.currentIndexChanged.connect(self.load_current_parent_email)
        
        return tab

    def load_parent_emails(self):
        """Load all parent emails with search functionality"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            
            search_term = self.parent_search.text()
            
            query = """
                SELECT u.id as student_id, u.name as student_name, p.email as parent_email
                FROM users u
                LEFT JOIN parents p ON u.id = p.student_id
                WHERE u.role = 'student'
            """
            
            params = []
            
            if search_term:
                query += " AND (u.name LIKE %s OR p.email LIKE %s)"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY u.name"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            self.parent_emails_table.setRowCount(len(results))
            
            for row_idx, record in enumerate(results):
                self.parent_emails_table.setItem(row_idx, 0, QTableWidgetItem(str(record['student_id'])))
                self.parent_emails_table.setItem(row_idx, 1, QTableWidgetItem(record['student_name']))
                
                email = record['parent_email'] if record['parent_email'] else "Not set"
                email_item = QTableWidgetItem(email)
                
                if not record['parent_email']:
                    email_item.setBackground(QColor(255, 230, 230))  # Light red for missing emails
                    
                self.parent_emails_table.setItem(row_idx, 2, email_item)
                
        except Exception as e:
            print(f"Error loading parent emails: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def export_parent_emails_csv(self):
        """Export parent emails to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Parent Emails", "", "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Student ID", "Student Name", "Parent Email"])
                
                for row in range(self.parent_emails_table.rowCount()):
                    writer.writerow([
                        self.parent_emails_table.item(row, 0).text(),
                        self.parent_emails_table.item(row, 1).text(),
                        self.parent_emails_table.item(row, 2).text()
                    ])
            
            QMessageBox.information(self, "Success", "Parent emails exported to CSV successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def load_student_combo(self):
        """Load students into the combo box with indication of parent email status"""
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.id, u.name, p.email IS NOT NULL as has_parent_email
                FROM users u
                LEFT JOIN parents p ON u.id = p.student_id
                WHERE u.role = 'student'
                ORDER BY u.name
            """)
            students = cursor.fetchall()
            
            self.student_combo.clear()
            for student in students:
                display_text = f"{student['name']}"
                if student['has_parent_email']:
                    display_text += " (email set)"
                self.student_combo.addItem(display_text, student['id'])
                
        except Exception as e:
            print(f"Error loading students: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def load_current_parent_email(self):
        """Load the current parent email for the selected student"""
        student_id = self.student_combo.currentData()
        if not student_id:
            return
            
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT email FROM parents WHERE student_id = %s", (student_id,))
            result = cursor.fetchone()
            
            if result:
                self.current_email_label.setText(f"Current parent email: {result['email']}")
                self.parent_email_input.setText(result['email'])
                self.current_email_label.setStyleSheet("color: green; font-style: italic;")
            else:
                self.current_email_label.setText("No parent email set for this student")
                self.parent_email_input.clear()
                self.current_email_label.setStyleSheet("color: red; font-style: italic;")
                
        except Exception as e:
            print(f"Error loading parent email: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    def save_parent_email(self):
        """Save or update the parent email for the selected student"""
        student_id = self.student_combo.currentData()
        email = self.parent_email_input.text().strip()
        
        if not student_id:
            QMessageBox.warning(self, "Error", "Please select a student")
            return
            
        if not email or "@" not in email or "." not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
            
        conn = connect_db()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Check if parent record exists
            cursor.execute("SELECT id FROM parents WHERE student_id = %s", (student_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing record
                cursor.execute("UPDATE parents SET email = %s WHERE student_id = %s", 
                             (email, student_id))
                action = "updated"
            else:
                # Insert new record
                cursor.execute("INSERT INTO parents (student_id, email) VALUES (%s, %s)", 
                             (student_id, email))
                action = "added"
                
            conn.commit()
            QMessageBox.information(self, "Success", f"Parent email {action} successfully")
            
            # Refresh all views
            self.load_current_parent_email()
            self.load_parent_emails()
            self.load_student_combo()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save parent email: {e}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
                

if __name__ == "__main__":
    # Create assets directory if it doesn't exist
    if not os.path.exists("assets"):
        os.makedirs("assets")
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set default font
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # Initialize database
    create_tables()
    
    window = FaceAttendanceSystem()
    window.show()
    
    sys.exit(app.exec())