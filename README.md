# Backup Manager

Une application web Flask pour la gestion des sauvegardes OneDrive sur Debian.

## Fonctionnalités

- **Authentification Utilisateur** : Système d'authentification sécurisé pour l'accès utilisateur.
- **Montage OneDrive** : Montage automatique de OneDrive via Rclone après connexion.
- **Sauvegarde des données** : Compression et sauvegarde des dossiers OneDrive montés.
- **Gestion des sauvegardes** : Interface intuitive pour gérer et télécharger les archives.
- **Rétention paramétrables** : Configuration du nombre de jours de conservation des sauvegardes.
- **Notifications par email** : Alertes automatiques lors des opérations de sauvegarde.
- **Interface d'administration** : Gestion des utilisateurs et des paramètres système.

## Prérequis

- Python 3.8+
- Flask et extensions
- Rclone installé et configuré
- Debian ou dérivé Linux
- Accès SuperUtilisateur (pour les opérations de montage)

## Installation

1. Cloner le dépôt :
```bash
git clone https://github.com/BadrBouzakri/Backup-manager.git
cd Backup-manager
```

2. Créer un environnement virtuel et installer les dépendances :
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Configurer Rclone pour OneDrive :
```bash
rclone config
```
Suivez les instructions pour configurer les accès OneDrive.

4. Créer un fichier .env pour les variables d'environnement :
```bash
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=votre-cle-secrete
DATABASE_URI=sqlite:///app.db
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=votre-email@example.com
MAIL_PASSWORD=votre-mot-de-passe
```

5. Initialiser la base de données et créer un utilisateur administrateur :
```bash
flask shell
```
```python
from app import db
from app.models import User
db.create_all()
admin = User(username='admin', email='admin@example.com', password='mot-de-passe-admin', is_admin=True)
db.session.add(admin)
db.session.commit()
exit()
```

## Exécution

Pour démarrer l'application :
```bash
python run.py
```

L'application sera accessible à l'adresse : http://localhost:5000

## Configuration pour la production

En production, il est recommandé d'utiliser Gunicorn et Nginx :

1. Installer Gunicorn :
```bash
pip install gunicorn
```

2. Créer un fichier de service systemd `/etc/systemd/system/backup-manager.service` :
```
[Unit]
Description=Backup Manager
After=network.target

[Service]
User=www-data
WorkingDirectory=/chemin/vers/Backup-manager
ExecStart=/chemin/vers/Backup-manager/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Configurer Nginx comme proxy inverse :
```
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

4. Activer et démarrer le service :
```bash
sudo systemctl enable backup-manager
sudo systemctl start backup-manager
```

## Sécurité

- Assurez-vous que les permissions sont correctement configurées
- Modifiez les mots de passe par défaut
- Utilisez HTTPS en production
- Limitez l'accès aux fichiers de configuration sensibles

## License

Ce projet est sous licence MIT.
