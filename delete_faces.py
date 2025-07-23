import os
import glob

# Jitne bhi "detected_face_*.jpg" ya "face_*.jpg" hai, unko delete karega
for file in glob.glob("detected_face_*.jpg") + glob.glob("saved_faces/face_*.jpg"):
    os.remove(file)
    print(f"🗑️ Deleted: {file}")

print("✅ Saare unwanted face files delete ho gaye!")
