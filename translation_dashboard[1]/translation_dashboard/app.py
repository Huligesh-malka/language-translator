from flask import Flask, render_template, request, jsonify, redirect
from gtts.lang import tts_langs
from deep_translator import GoogleTranslator
from textblob import TextBlob
from gtts import gTTS
from langdetect import detect, DetectorFactory
from PIL import Image
from werkzeug.utils import secure_filename
from docx import Document
from PyPDF2 import PdfReader
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import pytesseract
import time
import uuid
import json
import os
import fitz  # PyMuPDF
import docx

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)
app.secret_key = 'Shivu#77'  # 🔐 Make this unique and secret


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

bcrypt = Bcrypt(app)

users_file = "users.json"
if not os.path.exists(users_file):
    with open(users_file, "w") as f:
        json.dump({}, f)
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        with open(users_file, 'r+') as f:
            try:
                users = json.load(f)
                if not isinstance(users, dict):  # 👈 important check
                    users = {}
            except json.JSONDecodeError:
                users = {}

            if username in users:
                return "User already exists"

            users[username] = password
            f.seek(0)
            json.dump(users, f, indent=4)
            f.truncate()

        return redirect('/login')
    return render_template("signup.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with open(users_file, 'r') as f:
            users = json.load(f)

        if username in users and bcrypt.check_password_hash(users[username], password):
            user = User(username)
            login_user(user)
            return redirect('/menu')
        else:
            return "Invalid credentials"
    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@app.route('/document')
def document_page():
    languages = GoogleTranslator().get_supported_languages(as_dict=True)
    return render_template("document.html", languages=languages)

from werkzeug.utils import secure_filename
from docx import Document
from PyPDF2 import PdfReader
import uuid

@app.route('/document-translate', methods=['POST'])
def document_translate():
    if 'document' not in request.files:
        return render_template("document.html", error="No file uploaded", languages=GoogleTranslator().get_supported_languages(as_dict=True))
    
    file = request.files['document']
    if file.filename == '':
        return render_template("document.html", error="No file selected", languages=GoogleTranslator().get_supported_languages(as_dict=True))
    
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    temp_path = os.path.join("static/uploads", f"{uuid.uuid4()}{ext}")
    os.makedirs("static/uploads", exist_ok=True)
    file.save(temp_path)

    # Read text
    text = ""
    try:
        if ext == ".txt":
            with open(temp_path, "r", encoding="utf-8") as f:
                text = f.read()
        elif ext == ".pdf":
            reader = PdfReader(temp_path)
            for page in reader.pages:
                text += page.extract_text()
        elif ext == ".docx":
            doc = Document(temp_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            return render_template("document.html", error="Unsupported file format", languages=GoogleTranslator().get_supported_languages(as_dict=True))
        
        # Translate
        target_lang = request.form.get("target", "english").lower()
        translated_text = GoogleTranslator(source="auto", target=target_lang).translate(text)

        # Save translated text
        translated_filename = f"translated_{uuid.uuid4()}.txt"
        translated_path = os.path.join("static/translated_docs", translated_filename)
        os.makedirs("static/translated_docs", exist_ok=True)
        with open(translated_path, "w", encoding="utf-8") as f:
            f.write(translated_text)

        # Render with download button
        return render_template("document.html", download_link=f"/{translated_path}", languages=GoogleTranslator().get_supported_languages(as_dict=True))

    except Exception as e:
        return render_template("document.html", error=str(e), languages=GoogleTranslator().get_supported_languages(as_dict=True))


# Load or create history
history_file = "history.json"
if not os.path.exists(history_file):
    with open(history_file, "w") as f:
        json.dump([], f)

@app.route('/menu')
@login_required
def menu():
    return render_template("menu.html")

@app.route('/text')
def text_translation():
    languages = GoogleTranslator().get_supported_languages(as_dict=True)
    return render_template("index.html", languages=languages)

@app.route('/image')
def image_translation_page():
    languages = GoogleTranslator().get_supported_languages(as_dict=True)
    return render_template("image.html", languages=languages)

@app.route('/image-translate', methods=['POST'])
def image_translate():
    languages = GoogleTranslator().get_supported_languages(as_dict=True)
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    # Save image temporarily
    image_path = os.path.join("static/uploads", file.filename)
    os.makedirs("static/uploads", exist_ok=True)
    file.save(image_path)

    try:
        # Extract text using OCR
        extracted_text = pytesseract.image_to_string(Image.open(image_path))

        # Translate the extracted text
        target_lang = request.form.get("target", "english").lower()
        translated = GoogleTranslator(source="auto", target=target_lang).translate(extracted_text)

        return render_template("image.html", languages=languages,
            extracted_text=extracted_text,
            translation=translated
        )
    except Exception as e:
        return render_template("image.html", languages=languages, error=str(e))



def save_history(entry):
    if not current_user.is_authenticated:
        return

    try:
        with open(history_file, "r+") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []

            user_entry = {"user": current_user.id, **entry}
            data.append(user_entry)
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
    except Exception as e:
        print(f"Error saving history:{e}")


@app.route('/')
def index():
    return redirect('/login')


from gtts.lang import tts_langs  # Import available languages in gTTS


DetectorFactory.seed=0
@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get("text", "").strip()
    # Spell correction
    corrected_text = str(TextBlob(text).correct())

    source = data.get("source", "auto")
    target = data.get("target", "english").lower().strip()

    try:
        if not text :
            return jsonify({"error":"No text provided"}),
        detected_lang=detect(corrected_text) if source=="auto" else source
        translated = GoogleTranslator(source=detected_lang, target=target).translate(corrected_text)
        
        result = {
            "original": text,
            "translated": translated,
            "corrected": corrected_text,
            "source": detected_lang,
            "target": target
        }
        save_history(result)

        # Convert `target` to gTTS-compatible language code
        gtts_lang = {v.lower(): k for k, v in tts_langs().items()}  # Reverse map
        target_code = gtts_lang.get(target, "en")  # Default to "en" if not found

        # Ensure "static/audio" directory exists
        audio_dir = "static/audio"
        os.makedirs(audio_dir, exist_ok=True)

        # Generate and save speech audio
        tts = gTTS(translated, lang=target_code)  # Use valid gTTS code
        filename = f"{audio_dir}/{uuid.uuid4()}.mp3"
        tts.save(filename)
        result["audio_url"] = "/" + filename  # Ensure correct path

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})
    

@app.route('/history')
@login_required
def get_history():
    try:
        with open(history_file, "r") as file:
            data = json.load(file)
            user_data = [entry for entry in data if entry.get("user") == current_user.id]
            return jsonify(user_data)
    except Exception as e:
        return jsonify({"error": str(e)})



# Delete old audio files (older than 10 minutes)
def clean_old_audio():
    audio_folder = "static/audio"
    now = time.time()
    for filename in os.listdir(audio_folder):
        file_path = os.path.join(audio_folder, filename)
        if os.path.isfile(file_path) and filename.endswith(".mp3"):
            if now - os.path.getmtime(file_path) > 600:  # 600 seconds = 10 minutes
                os.remove(file_path)

# Run cleanup when the app starts
clean_old_audio()



if __name__ == '__main__':
    app.run(debug=True)
