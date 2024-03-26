import cv2
import os
import face_recognition
import datetime
from connection import conn
from flask import Flask, render_template, request, redirect, url_for
import re
import subprocess

app = Flask(__name__)

known_faces = []
known_names = []

today = datetime.date.today().strftime("%d_%m_%Y")

def get_known_encodings():
    global known_faces, known_names
    known_faces = []
    known_names = []
    for filename in os.listdir('static/faces'):
        image = face_recognition.load_image_file(os.path.join('static/faces', filename))
        face_encodings = face_recognition.face_encodings(image)
        if face_encodings:  # Check if any face encodings are detected
            encoding = face_encodings[0]  # Assuming only one face per image
            known_faces.append(encoding)
            known_names.append(os.path.splitext(filename)[0])

def totalreg():
    return len(os.listdir('static/faces/'))

def extract_attendance():
    results = conn.read(f"SELECT * FROM {today}")
    return results

def mark_attendance(person):
    name_roll = person.rsplit('_', 1)
    name = name_roll[0]
    roll_no = name_roll[1]
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    exists = conn.read(f"SELECT * FROM {today} WHERE roll_no = %s", (roll_no,))
    if exists is not None:  # Check if exists is not None
        if len(exists) == 0:
            try:
                conn.insert(f"INSERT INTO {today} VALUES (%s, %s, %s)", (name, roll_no, current_time))
            except Exception as e:
                print(e)
    else:
        print("No data returned from the query.")
    
def identify_person():
    video_capture = cv2.VideoCapture(0)
    attendance_marked = False
    while True:
        ret, frame = video_capture.read()
        rgb_frame = frame[:, :, ::-1]
        face_locations = face_recognition.face_locations(rgb_frame)
        if face_locations:  # Check if any face locations are detected
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            recognized_names = []
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_faces, face_encoding)
                name = 'Unknown'
                if True in matches:
                    matched_indices = [i for i, match in enumerate(matches) if match]
                    for index in matched_indices:
                        name = known_names[index]
                        recognized_names.append(name)
            if len(recognized_names) > 0:
                for name in recognized_names:
                    mark_attendance(name)
                attendance_marked = True
        cv2.imshow('camera', frame)
        if cv2.waitKey(1) & 0xFF == ord('q') or attendance_marked:
            break
    video_capture.release()
    cv2.destroyAllWindows()

def add_face_data_to_db(directory_path: str, conn):
    files_in_directory = os.listdir(directory_path)
    image_files = [file for file in files_in_directory if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print("No image files found in the directory!")
        return
    image_files.sort(key=lambda x: os.path.getctime(os.path.join(directory_path, x)))
    latest_image_filename = os.path.splitext(os.path.basename(image_files[-1]))[0]
    latest_image_path = os.path.join(directory_path, image_files[-1])
    conn.create("CREATE TABLE IF NOT EXISTS image_path (id INT AUTO_INCREMENT PRIMARY KEY, name TEXT NOT NULL, image_path TEXT NOT NULL, image LONGBLOB NOT NULL, FOREIGN KEY (roll_no) REFERENCES register_no(roll_no))")
    existing_paths = conn.read("SELECT image_path FROM image_path WHERE image_path = %s", (latest_image_path,))
    if existing_paths:
        print("Latest image path already exists in the table. Skipping insertion.")
        return
    face_id_result = conn.read("SELECT MAX(id) FROM image_path")
    if face_id_result and face_id_result[0][0] is not None:
        face_id = face_id_result[0][0] + 1
    else:
        face_id = 1
    with open(latest_image_path, 'rb') as image_file:
        image_data = image_file.read()
    conn.insert("INSERT INTO image_path (id, name, image_path, image) VALUES (%s, %s, %s, %s)", (face_id, latest_image_filename, latest_image_path, image_data))    
    print("Data inserted successfully.")   
    conn.close()
add_face_data_to_db("static/faces", conn)

def names_table(directory_path: str, conn):
    conn.create("CREATE TABLE IF NOT EXISTS person (id INT AUTO_INCREMENT PRIMARY KEY, fname VARCHAR(30), lname VARCHAR(30), FOREIGN KEY (roll_no) REFERENCES register_no(roll_no))")
    files_in_directory = os.listdir(directory_path)
    image_files = [file for file in files_in_directory if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print("No image files found in the directory!")
        return
    image_files.sort(key=lambda x: os.path.getctime(os.path.join(directory_path, x)))
    latest_image_path = os.path.join(directory_path, image_files[-1])
    match = re.match(r'^.*\\([^_]+)_([^_]+)_', latest_image_path)
    if match:
        fname, lname = match.groups()
    else:
        print("Filename doesn't match expected pattern.")
        return
    face_id_result = conn.read("SELECT MAX(id) FROM image_path")
    if face_id_result and face_id_result[0][0] is not None:
        face_id = face_id_result[0][0]
        existing_ids = [row[0] for row in conn.read("SELECT id FROM person")]
        if face_id in existing_ids:
            print("ID already exists in the person table.")
            return
        conn.insert("INSERT INTO person (id, fname, lname) VALUES (%s, %s, %s)", (face_id, fname, lname))
    else:
        print("No face ID found in the image_path table.")
    conn.close()
names_table("static/faces", conn)

def register_no_table(directory_path: str, conn):
    conn.create("CREATE TABLE IF NOT EXISTS register_no (id INT AUTO_INCREMENT PRIMARY KEY, roll_no VARCHAR(30), FOREIGN KEY (roll_no) REFERENCES register_no(roll_no))")
    files_in_directory = os.listdir(directory_path)
    image_files = [file for file in files_in_directory if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        print("No image files found in the directory!")
        return
    image_files.sort(key=lambda x: os.path.getctime(os.path.join(directory_path, x)))
    latest_image_path = os.path.join(directory_path, image_files[-1])
    match = re.search(r'(?<=_)[^_]+(?=\.[^.]+$)', latest_image_path)
    if match:
        roll_no = match.group()
    else:
        print("Roll number not found in filename.")
        return
    face_id_result = conn.read("SELECT MAX(id) FROM image_path")
    if face_id_result and face_id_result[0][0] is not None:
        face_id = face_id_result[0][0]
        conn.insert("INSERT IGNORE INTO register_no (id, roll_no) VALUES (%s, %s)", (face_id, roll_no))
        conn.close()
    else:
        print("No face ID found in the image_path table.")
register_no_table("static/faces", conn)

@app.route('/')
def home():
    conn.create(f"CREATE TABLE IF NOT EXISTS {today} (name VARCHAR(30), roll_no VARCHAR(20) PRIMARY KEY, time VARCHAR(10), FOREIGN KEY (roll_no) REFERENCES register_no(roll_no))")
    userDetails = extract_attendance()
    get_known_encodings()
    add_face_data_to_db("static/faces", conn)
    conn.close()
    return render_template('home.html', l=len(userDetails), today=today.replace("_", "-"), totalreg=totalreg(),
                           userDetails=userDetails)

@app.route('/video_feed', methods=['GET'])
def video_feed():
    identify_person()
    userDetails = extract_attendance()
    return redirect(url_for('home'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    name = request.form['newusername']
    roll_no = request.form['newrollno']
    phone_no = request.form['phone']
    email = request.form['email']
    userimagefolder = 'static/faces'
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    conn.create("""
    CREATE TABLE IF NOT EXISTS contact_details (
        id INT AUTO_INCREMENT PRIMARY KEY,
        phone_no VARCHAR(15),
        email VARCHAR(50)
    )
    """)
    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        print("Error: Unable to open camera")
        return redirect(url_for('home'))
    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("Error: Unable to capture frame")
            break
        flipped_frame = cv2.flip(frame, 1)
        text = "Press Q to Capture & Save the image"
        font = cv2.FONT_HERSHEY_COMPLEX
        font_scale = 0.9
        font_color = (0, 0, 200)
        thickness = 2
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (frame.shape[1] - text_size[0]) // 2
        text_y = (frame.shape[0] - 450)
        cv2.putText(flipped_frame, text, (text_x, text_y), font, font_scale, font_color, thickness, cv2.LINE_AA)
        cv2.imshow('camera', flipped_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            img_name = name + '_' + str(roll_no) + '.jpg'
            cv2.imwrite(os.path.join(userimagefolder, img_name), flipped_frame)
            break
    video_capture.release()
    cv2.destroyAllWindows()
    conn.insert("INSERT INTO contact_details (phone_no, email) VALUES (%s, %s)", (phone_no, email))
    subprocess.Popen(["python", "app.py"])
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)