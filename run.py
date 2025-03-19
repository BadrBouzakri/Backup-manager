#!/usr/bin/env python3
import os
from app import create_app
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Créer l'application avec la configuration spécifiée
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
