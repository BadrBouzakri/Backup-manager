import os
import subprocess
import datetime
import re
from flask import current_app
from app.models import Backup, Log, User
from app.onedrive import get_mount_path
from app import db
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Message
from app import mail

def run_backup(user_id):
    """
    Exécuter une sauvegarde pour un utilisateur
    """
    user = User.query.get(user_id)
    if not user:
        current_app.logger.error(f"Utilisateur non trouvé: {user_id}")
        return None
    
    # Obtenir le chemin de montage OneDrive
    mount_path = get_mount_path(user.username)
    if not mount_path:
        current_app.logger.error(f"OneDrive non monté pour {user.username}")
        return None
    
    # Créer le dossier de sauvegarde si nécessaire
    backup_path = os.path.join(current_app.config['BACKUP_PATH'], user.username)
    os.makedirs(backup_path, exist_ok=True)
    
    # Créer un horodatage pour le nom de fichier
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{user.username}_backup_{timestamp}.tar.gz"
    destination = os.path.join(backup_path, backup_filename)
    
    try:
        # Exécuter le script de sauvegarde
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts', 'backup.sh')
        
        # S'assurer que le script est exécutable
        os.chmod(script_path, 0o755)
        
        # Exécuter le script
        result = subprocess.run(
            [script_path, mount_path, backup_path, user.username],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            current_app.logger.error(f"Erreur lors de la sauvegarde: {result.stderr}")
            
            # Journalisation de l'échec
            log = Log(action="backup_failed", 
                     message=f"Échec de la sauvegarde pour {user.username}: {result.stderr}",
                     user_id=user.id)
            db.session.add(log)
            db.session.commit()
            return None
        
        # Récupérer le nom du fichier créé à partir de la sortie du script
        output = result.stdout
        match = re.search(r'Sauvegarde réussie: ([^\s]+)', output)
        if match:
            destination = match.group(1)
            backup_filename = os.path.basename(destination)
        
        # Créer une entrée de sauvegarde dans la base de données
        backup = Backup(
            filename=backup_filename,
            path=destination,
            user_id=user.id
        )
        db.session.add(backup)
        
        # Journalisation de la sauvegarde
        log = Log(action="backup_created", 
                 message=f"Sauvegarde créée pour {user.username}: {backup_filename}",
                 user_id=user.id)
        db.session.add(log)
        db.session.commit()
        
        # Purger les sauvegardes obsolètes
        clean_old_backups(user.id)
        
        # Envoyer une notification
        if current_app.config.get('MAIL_USERNAME') and current_app.config.get('MAIL_PASSWORD'):
            send_backup_notification(user, backup)
        
        current_app.logger.info(f"Sauvegarde créée pour {user.username}: {backup_filename}")
        return backup
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
        
        # Journalisation de l'erreur
        log = Log(action="backup_error", 
                 message=f"Erreur lors de la sauvegarde pour {user.username}: {str(e)}",
                 user_id=user.id)
        db.session.add(log)
        db.session.commit()
        return None

def clean_old_backups(user_id):
    """
    Supprimer les sauvegardes plus anciennes que la rétention configurée
    """
    user = User.query.get(user_id)
    if not user:
        current_app.logger.error(f"Utilisateur non trouvé: {user_id}")
        return False
    
    retention_days = user.retention_days or current_app.config['DEFAULT_RETENTION_DAYS']
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
    
    # Obtenir toutes les sauvegardes plus anciennes que la date limite
    old_backups = Backup.query.filter(
        Backup.user_id == user_id,
        Backup.created_at < cutoff_date
    ).all()
    
    for backup in old_backups:
        try:
            # Supprimer le fichier
            if os.path.exists(backup.path):
                os.remove(backup.path)
            
            # Supprimer l'entrée de la base de données
            db.session.delete(backup)
            
            # Journalisation de la suppression
            log = Log(action="backup_deleted", 
                     message=f"Sauvegarde supprimée pour {user.username}: {backup.filename}",
                     user_id=user.id)
            db.session.add(log)
        
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la suppression d'une sauvegarde: {str(e)}")
    
    db.session.commit()
    return True

def get_user_backups(user_id):
    """
    Obtenir toutes les sauvegardes d'un utilisateur
    """
    return Backup.query.filter_by(user_id=user_id).order_by(Backup.created_at.desc()).all()

def delete_backup(backup_id, user_id=None):
    """
    Supprimer une sauvegarde spécifique
    """
    if user_id:
        backup = Backup.query.filter_by(id=backup_id, user_id=user_id).first()
    else:
        backup = Backup.query.get(backup_id)
    
    if not backup:
        current_app.logger.error(f"Sauvegarde non trouvée: {backup_id}")
        return False
    
    user = User.query.get(backup.user_id)
    
    try:
        # Supprimer le fichier
        if os.path.exists(backup.path):
            os.remove(backup.path)
        
        # Supprimer l'entrée de la base de données
        db.session.delete(backup)
        
        # Journalisation de la suppression
        log = Log(action="backup_deleted_manual", 
                 message=f"Sauvegarde supprimée manuellement: {backup.filename}",
                 user_id=backup.user_id)
        db.session.add(log)
        
        db.session.commit()
        
        current_app.logger.info(f"Sauvegarde supprimée: {backup.filename}")
        return True
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la suppression d'une sauvegarde: {str(e)}")
        return False

def send_backup_notification(user, backup):
    """
    Envoyer une notification par email pour une sauvegarde
    """
    try:
        size_str = backup.get_size_str()
        subject = f"Sauvegarde OneDrive - {backup.filename}"
        
        # Créer le message
        msg = Message(
            subject=subject,
            recipients=[user.email],
            body=f"""Bonjour {user.username},

Une nouvelle sauvegarde de votre dossier OneDrive a été créée avec succès.

Détails de la sauvegarde:
- Nom du fichier: {backup.filename}
- Date de création: {backup.created_at.strftime('%d/%m/%Y %H:%M:%S')}
- Taille: {size_str}

Vous pouvez télécharger cette sauvegarde depuis l'application Backup Manager.

Cordialement,
L'équipe Backup Manager
"""
        )
        
        # Envoyer l'email
        mail.send(msg)
        
        # Journalisation de l'envoi
        log = Log(action="notification_sent", 
                 message=f"Notification envoyée pour la sauvegarde {backup.filename}",
                 user_id=user.id)
        db.session.add(log)
        db.session.commit()
        
        current_app.logger.info(f"Notification envoyée pour la sauvegarde {backup.filename}")
        return True
    
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'envoi de la notification: {str(e)}")
        return False
