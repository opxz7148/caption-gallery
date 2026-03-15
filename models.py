from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('email', name='uq_user_email'),
    )
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    

class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('user.id', name='fk_picture_user_id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f'<Picture {self.filename}>'