import os
import subprocess
import logging
import json
from flask import current_app
from app.models import Log
from app import db
import shutil

def init_rclone_config():
    """
    Initialiser la configuration rclone si elle n'existe pas
    """
    config_path = current_app.config['RCLONE_CONFIG_PATH']
    
    # Vérifier si le fichier de configuration existe déjà
    if not os.path.exists(config_path):
        # Créer le répertoire parent si nécessaire
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Créer un fichier de configuration vide
        with open(config_path, 'w') as f:
            f.write("# Rclone configuration file for Backup Manager\n")
        
        # Journaliser l'initialisation
        log = Log(action="rclone_init", message="Initialisation du fichier de configuration Rclone")
        db.session.add(log)
        db.session.commit()
        
        current_app.logger.info(f"Fichier de configuration Rclone créé: {config_path}")
    
    return config_path

def check_onedrive_config(username):
    """
    Vérifier si la configuration OneDrive existe pour l'utilisateur
    """
    config_path = current_app.config['RCLONE_CONFIG_PATH']
    
    # Vérifier si le fichier de configuration existe
    if not os.path.exists(config_path):
        init_rclone_config()
        return False
    
    # Vérifier si l'utilisateur a une section de configuration
    try:
        result = subprocess.run(
            ['rclone', 'config', 'dump', f'--config={config_path}'],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            current_app.logger.error(f"Erreur lors de la vérification de la configuration OneDrive: {result.stderr}")
            return False
        
        # Analyser la sortie JSON
        config = json.loads(result.stdout)
        remote_name = f"onedrive_{username}"
        
        return remote_name in config
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la vérification de la configuration OneDrive: {str(e)}")
        return False

def setup_onedrive_config(username, client_id, client_secret, refresh_token=None):
    """
    Configurer OneDrive pour un utilisateur avec Rclone
    """
    config_path = current_app.config['RCLONE_CONFIG_PATH']
    remote_name = f"onedrive_{username}"
    
    try:
        # Si refresh_token est fourni, nous pouvons créer directement la configuration
        if refresh_token:
            config_data = {
                "type": "onedrive",
                "client_id": client_id,
                "client_secret": client_secret,
                "token": refresh_token
            }
            
            # Créer un fichier de configuration temporaire
            temp_config = f"""[{remote_name}]
type = onedrive
client_id = {client_id}
client_secret = {client_secret}
token = {refresh_token}
"""
            temp_config_path = os.path.join(os.path.dirname(config_path), f"temp_{username}.conf")
            with open(temp_config_path, 'w') as f:
                f.write(temp_config)
            
            # Fusionner les configurations
            result = subprocess.run(
                ['rclone', 'config', 'file', temp_config_path, 'file', config_path],
                capture_output=True, text=True
            )
            
            # Supprimer le fichier temporaire
            os.remove(temp_config_path)
            
            if result.returncode != 0:
                current_app.logger.error(f"Erreur lors de la configuration de OneDrive: {result.stderr}")
                return False
        else:
            # Si pas de refresh_token, l'utilisateur doit configurer manuellement
            # Dans une application réelle, vous devriez implémenter OAuth2 approprié ici
            current_app.logger.warning("Configuration manuelle requise pour OneDrive. Implémentez OAuth2.")
            return False
        
        # Journalisation de la configuration
        log = Log(action="onedrive_setup", 
                 message=f"Configuration de OneDrive pour l'utilisateur {username}")
        db.session.add(log)
        db.session.commit()
        
        return True
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la configuration de OneDrive: {str(e)}")
        return False

def mount_onedrive(username, onedrive_folder=None):
    """
    Monter le dossier OneDrive pour un utilisateur
    """
    config_path = current_app.config['RCLONE_CONFIG_PATH']
    mount_base = current_app.config['RCLONE_MOUNT_BASE']
    remote_name = f"onedrive_{username}"
    
    # Si pas de dossier spécifié, utiliser le nom d'utilisateur
    if not onedrive_folder:
        onedrive_folder = username
    
    # Créer le chemin de montage
    mount_path = os.path.join(mount_base, username)
    
    # Vérifier si le dossier de montage existe
    if not os.path.exists(mount_path):
        os.makedirs(mount_path, exist_ok=True)
    
    # Vérifier si la configuration OneDrive existe
    if not check_onedrive_config(username):
        current_app.logger.warning(f"Configuration OneDrive manquante pour {username}")
        return None
    
    # Vérifier si le dossier est déjà monté
    if os.path.ismount(mount_path):
        current_app.logger.info(f"OneDrive déjà monté pour {username} à {mount_path}")
        return mount_path
    
    try:
        # Construire la commande de montage
        remote_path = f"{remote_name}:{onedrive_folder}"
        mount_cmd = [
            'rclone', 'mount',
            f'--config={config_path}',
            '--daemon',  # Exécuter en arrière-plan
            '--allow-other',  # Permettre à d'autres utilisateurs d'accéder
            '--vfs-cache-mode=writes',  # Mettre en cache les écritures
            remote_path, mount_path
        ]
        
        # Exécuter la commande
        result = subprocess.run(mount_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            current_app.logger.error(f"Erreur lors du montage OneDrive: {result.stderr}")
            return None
        
        # Journalisation du montage
        log = Log(action="onedrive_mount", 
                 message=f"Montage OneDrive pour {username} à {mount_path}")
        db.session.add(log)
        db.session.commit()
        
        current_app.logger.info(f"OneDrive monté pour {username} à {mount_path}")
        return mount_path
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors du montage OneDrive: {str(e)}")
        return None

def unmount_onedrive(username):
    """
    Démonter le dossier OneDrive d'un utilisateur
    """
    mount_base = current_app.config['RCLONE_MOUNT_BASE']
    mount_path = os.path.join(mount_base, username)
    
    # Vérifier si le dossier est monté
    if not os.path.exists(mount_path) or not os.path.ismount(mount_path):
        current_app.logger.info(f"OneDrive non monté pour {username}")
        return True
    
    try:
        # Démonter avec fusermount
        result = subprocess.run(['fusermount', '-u', mount_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            # Essayer avec umount si fusermount échoue
            result = subprocess.run(['umount', mount_path], capture_output=True, text=True)
            
            if result.returncode != 0:
                current_app.logger.error(f"Erreur lors du démontage OneDrive: {result.stderr}")
                return False
        
        # Journalisation du démontage
        log = Log(action="onedrive_unmount", 
                 message=f"Démontage OneDrive pour {username} de {mount_path}")
        db.session.add(log)
        db.session.commit()
        
        current_app.logger.info(f"OneDrive démonté pour {username} de {mount_path}")
        return True
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors du démontage OneDrive: {str(e)}")
        return False

def get_mount_path(username):
    """
    Obtenir le chemin de montage pour un utilisateur
    """
    mount_base = current_app.config['RCLONE_MOUNT_BASE']
    mount_path = os.path.join(mount_base, username)
    
    if os.path.exists(mount_path) and os.path.ismount(mount_path):
        return mount_path
    
    return None
