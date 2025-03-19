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

- Docker et Docker Compose (pour le déploiement avec Docker)
- OU Python 3.8+, Flask et extensions, Rclone pour une installation manuelle
- Debian ou dérivé Linux
- Accès SuperUtilisateur (pour les opérations de montage)

## Installation avec Docker (recommandé)

1. Cloner le dépôt :
```bash
git clone https://github.com/BadrBouzakri/Backup-manager.git
cd Backup-manager
```

2. Créer un fichier .env à partir de .env.example :
```bash
cp .env.example .env
```
Éditez le fichier .env selon vos besoins.

3. Lancer l'application avec Docker Compose :
```bash
docker-compose up -d
```

4. L'application sera accessible à l'adresse : http://localhost:5000
   - Nom d'utilisateur administrateur par défaut : `admin`
   - Mot de passe par défaut : `admin`

5. Pour configurer Rclone pour OneDrive, vous pouvez exécuter :
```bash
docker-compose exec web rclone config
```

## Installation manuelle

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

6. Démarrer l'application :
```bash
python run.py
```

## Utilisation des montages OneDrive avec Docker

Pour que les montages OneDrive fonctionnent correctement avec Docker, vous devez lancer le conteneur avec les privilèges appropriés :

1. Le conteneur est configuré avec `--cap-add SYS_ADMIN` et `--device /dev/fuse:/dev/fuse`
2. L'option `--security-opt apparmor:unconfined` est ajoutée pour contourner les restrictions AppArmor

Pour configurer un nouvel accès OneDrive dans Docker :

1. Exécutez la commande de configuration Rclone :
```bash
docker-compose exec web rclone config
```

2. Suivez les instructions pour ajouter un nouveau "remote" pour OneDrive
3. Le fichier de configuration sera stocké dans le volume persistant

## Sauvegarde et restauration des données Docker

Pour sauvegarder l'ensemble de l'application :

```bash
# Sauvegarde des volumes
docker run --rm -v backup-manager_postgres-data:/dbdata -v $(pwd):/backup ubuntu tar czf /backup/postgres-data.tar.gz /dbdata
docker run --rm -v backup-manager_backup-storage:/storage -v $(pwd):/backup ubuntu tar czf /backup/backup-storage.tar.gz /storage
docker run --rm -v backup-manager_backup-logs:/logs -v $(pwd):/backup ubuntu tar czf /backup/backup-logs.tar.gz /logs

# Sauvegarde de la configuration
cp -r instance backup-config
```

Pour restaurer :

```bash
# Restauration des volumes
docker run --rm -v backup-manager_postgres-data:/dbdata -v $(pwd):/backup ubuntu bash -c "cd /dbdata && tar xzf /backup/postgres-data.tar.gz --strip 1"
docker run --rm -v backup-manager_backup-storage:/storage -v $(pwd):/backup ubuntu bash -c "cd /storage && tar xzf /backup/backup-storage.tar.gz --strip 1"
docker run --rm -v backup-manager_backup-logs:/logs -v $(pwd):/backup ubuntu bash -c "cd /logs && tar xzf /backup/backup-logs.tar.gz --strip 1"

# Restauration de la configuration
cp -r backup-config/instance .
```

## Sécurité

- Assurez-vous que les permissions sont correctement configurées
- Modifiez les mots de passe par défaut après la première connexion
- Utilisez HTTPS en production (configurez un reverse proxy comme Nginx avec Let's Encrypt)
- Limitez l'accès aux fichiers de configuration sensibles

## License

Ce projet est sous licence MIT.
