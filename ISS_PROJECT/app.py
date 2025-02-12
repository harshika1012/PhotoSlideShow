import os
import io
import base64
import tempfile
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify, send_from_directory, redirect, url_for, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from moviepy.editor import ImageSequenceClip, AudioFileClip, concatenate_audioclips, vfx
from mutagen.mp3 import MP3
from datetime import datetime
import psycopg2
from psycopg2 import sql
import os
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from mutagen.wavpack import WavPack

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploaded_images'
app.config['SECRET_KEY'] = 'your_secret_key_here'
conn = psycopg2.connect(os.environ["DATABASE_URL"])

cur = conn.cursor()


def create_tables():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(80) NOT NULL,
        username VARCHAR(80) UNIQUE NOT NULL,
        email VARCHAR(120) UNIQUE NOT NULL,
        password VARCHAR(1024) NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id SERIAL PRIMARY KEY,
        user_id INTEGER  NULL,
        binary_image BYTEA NOT NULL,
        size INTEGER NOT NULL,
        extension VARCHAR(10)  ,
        width INTEGER  ,
        height INTEGER  
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audios (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        duration FLOAT NOT NULL,
        binary_audio BYTEA NOT NULL
    )
    """)
    conn.commit()


# Assume conn and cur are already initialized
def get_audio_duration(file_path):
    audio_extension = os.path.splitext(file_path)[1].lower()
    try:
        if audio_extension == '.mp3':
            audio = MP3(file_path)
            return audio.info.length
        elif audio_extension == '.mp4':
            audio = MP4(file_path)
            return audio.info.length
        elif audio_extension == '.ogg':
            audio = OggVorbis(file_path)
            return audio.info.length
        elif audio_extension == '.flac':
            audio = FLAC(file_path)
            return audio.info.length
        elif audio_extension == '.wv':
            audio = WavPack(file_path)
            return audio.info.length
        else:
            # Handle other audio formats if needed
            return 0.0  # Default duration if format is not supported
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0.0  # Default duration if an error occurs

def insert_audios_from_folder(folder_path):
    try:
        # List all files in the folder
        files = os.listdir(folder_path)

        for file_name in files:
            file_path = os.path.join(folder_path, file_name)

            # Read the file content
            with open(file_path, 'rb') as file:
                audio_content = file.read()

            # Get audio duration using mutagen
            audio_duration = get_audio_duration(file_path)

            # Insert the audio into the database
            cur.execute(sql.SQL("""
                INSERT INTO audios (name, duration, binary_audio)
                VALUES (%s, %s, %s)
            """), (file_name, audio_duration, psycopg2.Binary(audio_content)))

        conn.commit()
        print("Audios inserted successfully!")
    except Exception as e:
        print(f"Error inserting audios: {e}")

@app.route('/')
def index_page():
    return render_template('index.html')

# @app.route('/signup', methods=['POST','GET'])
# def signup():
#     if request.method == 'POST':
#         username = request.form['username']
#         name = request.form['name']
#         email = request.form['email']
#         password = request.form['password']
#         hash_pswd = generate_password_hash(password)
#         cur.execute("""
#         INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)
#         """, (name, username, email, hash_pswd))
#         conn.commit()
#         return jsonify({'message': 'User created successfully!'})
#     return render_template('signup.html')

@app.route('/signup', methods=['POST','GET'])
def signup():
    try:
        if request.method == 'POST':
            username = request.form['username']
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            hash_pswd = generate_password_hash(password)
            cur.execute("""
            INSERT INTO users (name, username, email, password) VALUES (%s, %s, %s, %s)
            """, (name, username, email, hash_pswd))
            conn.commit()
            return jsonify({'message': 'User created successfully!'})
        return render_template('signup.html')
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

from flask import render_template, redirect, url_for, session

@app.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute("""
        SELECT * FROM users WHERE username = %s
        """, (username,))
        user = cur.fetchone()
        if user and check_password_hash(user[4], password):
            if username == 'admin' and password == 'admin':
                session['admin'] = True
                return redirect(url_for('admin'))
            else:
                session['user_id'] = user[0]
                return jsonify({'message': 'Login successful!'})
        return jsonify({'message': 'Login failed!'})
    return render_template('login.html')

@app.route('/admin')
def admin():
    if 'admin' not in session or not session['admin']:
        return redirect(url_for('index_page'))

    cur.execute("""
        SELECT username, email, password FROM users
    """)
    users_data = cur.fetchall()

    return render_template('admin.html', users=users_data)



# @app.route('/login', methods=['POST','GET'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         cur.execute("""
#         SELECT * FROM users WHERE username = %s
#         """, (username,))
#         user = cur.fetchone()
#         if user and check_password_hash(user[4], password):
#             session['user_id'] = user[0]
#             return jsonify({'message': 'Login successful!'})
#         return jsonify({'message': 'Login failed!'})
#     return render_template('login.html')

@app.route('/project/<username>', methods=['POST','GET'])
def project(username):
    return render_template('project.html',username=username)

# @app.route('/upload', methods=['POST','GET'])
# def upload_file():
#     user_id = session['user_id']  # Assume user_id is 1 for simplicity, should be retrieved from session or JWT token
#     file = request.files['file']
#     binary_image = file.read()
#     size = len(binary_image)
#     extension = file.filename.split('.')[-1]
#     cur.execute("""
#     INSERT INTO images (user_id, binary_image, size, extension) VALUES (%s, %s, %s, %s)
#     """, (user_id, binary_image, size, extension))
#     conn.commit()
#     return jsonify({'message': 'Image uploaded successfully!'})


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    files = request.files.getlist('file')

    for file in files:
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            # Read the file content
            file_content = file.read()

            # Insert the file into the database
            user_id = session.get('user_id', None)
            cur.execute("""
                INSERT INTO images (binary_image, size, extension, user_id) 
                VALUES (%s, %s, %s, %s)
                """, (psycopg2.Binary(file_content), len(file_content), file.filename.split('.')[-1], user_id))
            conn.commit()

    

    return jsonify({'message': 'Images uploaded successfully'}), 200
@app.route('/gallery')
def gallery():
    if 'user_id' not in session:
        return jsonify({'message': 'User not logged in'}), 401

    user_id = session['user_id']
    cur.execute("""
        SELECT binary_image, extension FROM images WHERE user_id = %s
    """, (user_id,))
    images = cur.fetchall()

    # Convert binary data to base64 for easier display in HTML
    images_data = []
    for image in images:
        image_data = {
            'binary_image': base64.b64encode(image[0]).decode('utf-8'),
            'extension': image[1]
        }
        images_data.append(image_data)

    return jsonify({'images': images_data}), 200





@app.route('/create_video', methods=['POST', 'GET'])
def create_video():
    data = request.get_json()
    images = data['images']  
    fps = 1/int(data['fps'])
    width = int(data['width'])
    height = int(data['height'])
    audios=data['audios']
    quality_val=int(data['quality'])

    try:

        video_clips = []

        # Iterate through the image URLs
        for image_url in images:
            # Decode the base64 encoded image
            image_data = base64.b64decode(image_url.split(',')[1])

            img = Image.open(io.BytesIO(image_data))

            if img.mode != 'RGB':
                img = img.convert('RGB')

            img = img.resize((width, height), resample=Image.BICUBIC)
            
            img_io = io.BytesIO()
            img.save(img_io, 'JPEG', quality=quality_val)
            img = Image.open(img_io)

            img_array = np.array(img)

            video_clips.append(img_array)

        if video_clips:
            final_clip = ImageSequenceClip(video_clips, fps=fps)
        else:
            print("No valid images provided.")
            return jsonify({"status": "failed", "message": "No valid images provided."})

       
        if audios != []:
            audio_clips = []

            for audio in audios:
                
                audio_data = base64.b64decode(audio['src'].split(',')[1])

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio_file:
                    temp_audio_file.write(audio_data)
                    temp_audio_path = temp_audio_file.name

                audio_clip = AudioFileClip(temp_audio_path)

                audio_clips.append(audio_clip)

            concatenated_audio = concatenate_audioclips(audio_clips)

            looped_audio = concatenated_audio.fx(vfx.loop, duration=final_clip.duration)

            final_clip = final_clip.set_audio(looped_audio)

        output_path = os.path.join('static', 'output_video.mp4')

        final_clip.write_videofile(output_path, codec='libx264')

        return jsonify({"status": "success", "output": output_path})

    except Exception as e:
        print(f"Error creating video: {e}")
        return jsonify({"status": "failed"})
    
@app.route('/videopage', methods=['POST', 'GET'])
def videodisplay():
    return render_template('videopage.html',target="_blank")


if __name__ == "__main__":
    create_tables()
    insert_audios_from_folder('static/audios')
    app.run(debug=True)


# @app.route('/video', methods=['GET', 'POST'])
# def video():
#     session = Session()
#     if 'user_id' in session:
#         user_id = session['user_id']
#         images = session.query(Image).filter_by(user_id=user_id).order_by(Image.id.desc()).all()
#         image_data = [{'path': os.path.join('images', image.path), 'id': image.id} for image in images]
#         audio_data = session.query(Audio).all()

#         if request.method == 'POST':
#             try:
#                 selected_images = request.form.get('selectedImages').split(',')
#                 selected_music = request.form.get('selectedMusic').split(',')
#                 duration = request.form.get('duration')
#                 effects = request.form.get('effects')
#                 resolution = request.form.get('resolution')
#                 quality = request.form.get('quality')

#                 resolution_width, resolution_height = map(int, resolution.split('×'))

#                 selected_images = [session.query(Image).get(int(id)) for id in selected_images]
#                 selected_music = [session.query(Audio).get(int(id)) for id in selected_music]

#                 image_clips = []
#                 for image in selected_images:
#                     clip = ImageClip(os.path.join(app.config['UPLOAD_FOLDER'], image.path), duration=int(duration))
#                     clip = resize(clip, newsize=(resolution_width, resolution_height))
#                     if effects == 'Fade In':
#                         clip = fadein(clip, int(duration))
#                     elif effects == 'Fade Out':
#                         clip = fadeout(clip, int(duration))
#                     elif effects== 'Zoom':
#                         clip = resize(clip, lambda t: 1 + 0.02 * t)
#                     elif effects == 'Dissolve':
#                         clip = clip.crossfadein(int(duration))
#                     image_clips.append(clip)

#                 audio_clips = [AudioFileClip(os.path.join(app.static_folder, audio.path)) for audio in selected_music]

#                 for clip in audio_clips:
#                     clip.duration = int(duration) * len(selected_images) / len(audio_clips)

#                 video = concatenate_videoclips(image_clips)
#                 audio = concatenate_audioclips(audio_clips)
#                 video = video.set_audio(audio)
#                 output_path = os.path.join(app.static_folder, "output.mp4")
#                 video.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', bitrate=quality)

#                 session['video_generated'] = True
#                 return redirect(url_for('video'))
#             except Exception as e:
#                 print(str(e))
#                 return "An error occurred while creating the video"
#         return render_template('video.html', image_data=image_data, audio_data=audio_data)
#     else:
#         return redirect('/login')

# @app.route('/reset_video_generated', methods=['POST'])
# def reset_video_generated():
#     session['video_generated'] = False
#     return '', 204



