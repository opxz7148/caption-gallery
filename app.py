from flask import Flask, render_template, request, redirect, url_for, abort, jsonify, send_from_directory
from flask_session import Session
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from caption_model import CaptionModel
import os
import logging
import time

from models import db, User, Picture

# Setup logging
logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.chmod(app.config['UPLOAD_FOLDER'], 0o755)
    app.logger.info(f"Upload folder created/verified: {app.config['UPLOAD_FOLDER']}")
except Exception as e:
    app.logger.error(f"Error creating upload folder: {e}")

# Initialize extensions
db.init_app(app)
Migrate(app, db)
Session(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

caption_model = CaptionModel()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Routes
@app.route('/')
@login_required
def home():
    pictures = []
    if current_user.is_authenticated:
        pictures = Picture.query.filter_by(user=current_user.id).all()
    
    return render_template('index.html', title='Welcome', pictures=pictures)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already exists')
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('home'))
    
    return render_template('register.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if file is in request
        if 'image' not in request.files:
            return render_template('upload.html', error='No image selected')
        
        file = request.files['image']
        
        if file.filename == '':
            return render_template('upload.html', error='No image selected')
        
        # Check file extension
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
            return render_template('upload.html', error='Only image files are allowed (png, jpg, jpeg, gif, webp)')
        
        # Save file
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        unique_filename = f"{int(time.time())}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Save to database
        picture = Picture(filename=unique_filename, user=current_user.id)
        db.session.add(picture)
        db.session.commit()
        
        return render_template('upload.html', success='Image uploaded successfully!')
    
    return render_template('upload.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/health')
def health():
    return {'status': 'ok'}, 200


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/picture/<int:picture_id>')
def picture(picture_id):
    picture = Picture.query.get_or_404(picture_id)
    return render_template('picture.html', picture=picture)

@app.route('/picture/<int:picture_id>/generate-caption', methods=['POST'])
@login_required
def generate_caption_api(picture_id):
    picture = Picture.query.get_or_404(picture_id)
    
    # Check if current user owns the picture
    if picture.user != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        # Use your existing caption function
        caption = caption_model.generate_caption(os.path.join(app.config['UPLOAD_FOLDER'], picture.filename))
        picture.caption = caption
        db.session.commit()
        
        return jsonify({'success': True, 'caption': caption})
    except Exception as e:
        app.logger.error(f"Error generating caption: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/caption/<int:picture_id>')
def caption(picture_id):
    picture = Picture.query.get_or_404(picture_id)
    caption = caption_model.generate_caption(os.path.join(app.config['UPLOAD_FOLDER'], picture.filename))
    picture.caption = caption
    db.session.commit()
    return redirect(url_for('picture', picture_id=picture_id))

# Error handlers
@app.errorhandler(403)
def forbidden(e):
    app.logger.error(f"403 Forbidden error: {e}")
    return render_template('error.html', code=403, message='Access Forbidden'), 403

@app.errorhandler(404)
def not_found(e):
    app.logger.error(f"404 Not Found error: {e}")
    return render_template('error.html', code=404, message='Page Not Found'), 404

@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"500 Server error: {e}")
    return render_template('error.html', code=500, message='Server Error'), 500


if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database initialized successfully")
        except Exception as e:
            app.logger.error(f"Database error: {e}")
    
    app.logger.info("Starting Flask app on http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000, debug=True)
