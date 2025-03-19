from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler
import os
from config import config

# Initialisation des extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'
bcrypt = Bcrypt()
mail = Mail()

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialisation des extensions avec l'application
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    
    # Configuration de la journalisation
    if not app.debug and not app.testing:
        if not os.path.exists(app.config['LOGS_PATH']):
            os.mkdir(app.config['LOGS_PATH'])
        
        file_handler = RotatingFileHandler(
            os.path.join(app.config['LOGS_PATH'], 'backup_manager.log'),
            maxBytes=10240,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Démarrage de Backup Manager')
    
    # Enregistrement des blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Créer les tables de la base de données si elles n'existent pas
    with app.app_context():
        db.create_all()
    
    return app

from app import models
