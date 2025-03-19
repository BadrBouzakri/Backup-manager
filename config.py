import os
from datetime import timedelta

class Config:
    # Application
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'un-secret-difficile-a-deviner'
    
    # Base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Chemin des dossiers
    STORAGE_PATH = os.environ.get('STORAGE_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage')
    BACKUP_PATH = os.environ.get('BACKUP_PATH') or os.path.join(STORAGE_PATH, 'backups')
    LOGS_PATH = os.environ.get('LOGS_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    
    # Configuration OneDrive/Rclone
    RCLONE_CONFIG_PATH = os.environ.get('RCLONE_CONFIG_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'rclone.conf')
    RCLONE_MOUNT_BASE = os.environ.get('RCLONE_MOUNT_BASE') or os.path.join(STORAGE_PATH, 'mounts')
    
    # Configuration de sauvegarde
    DEFAULT_RETENTION_DAYS = os.environ.get('DEFAULT_RETENTION_DAYS') or 2
    
    # Configuration de l'email (pour les notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'no-reply@example.com'
    
    # Création des dossiers nécessaires
    @staticmethod
    def init_app(app):
        os.makedirs(Config.STORAGE_PATH, exist_ok=True)
        os.makedirs(Config.BACKUP_PATH, exist_ok=True)
        os.makedirs(Config.LOGS_PATH, exist_ok=True)
        os.makedirs(Config.RCLONE_MOUNT_BASE, exist_ok=True)
        os.makedirs(os.path.dirname(Config.RCLONE_CONFIG_PATH), exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    
    # En production, utilisez une clé secrète plus sécurisée
    SECRET_KEY = os.environ.get('SECRET_KEY')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
