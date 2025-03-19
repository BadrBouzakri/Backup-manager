from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager, bcrypt
import os

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    onedrive_folder = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    backups = db.relationship('Backup', backref='user', lazy='dynamic')
    retention_days = db.Column(db.Integer, default=2)
    
    def __init__(self, username, email, password, is_admin=False, onedrive_folder=None, retention_days=2):
        self.username = username
        self.email = email
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        self.is_admin = is_admin
        self.onedrive_folder = onedrive_folder or username
        self.retention_days = retention_days
    
    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Backup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, nullable=True)  # Taille en octets
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __init__(self, filename, path, user_id, size=None):
        self.filename = filename
        self.path = path
        self.user_id = user_id
        
        # Calculer la taille du fichier si elle n'est pas fournie
        if size is None and os.path.exists(path):
            self.size = os.path.getsize(path)
        else:
            self.size = size
    
    def get_size_str(self):
        """Retourne la taille du fichier sous forme lisible"""
        if self.size is None:
            return "Inconnue"
        
        # Conversion en format lisible (KB, MB, GB)
        for unit in ['o', 'Ko', 'Mo', 'Go', 'To']:
            if self.size < 1024.0:
                return f"{self.size:.1f} {unit}"
            self.size /= 1024.0
    
    def __repr__(self):
        return f'<Backup {self.filename}>'

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, action, message, user_id=None):
        self.action = action
        self.message = message
        self.user_id = user_id
    
    def __repr__(self):
        return f'<Log {self.action}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
