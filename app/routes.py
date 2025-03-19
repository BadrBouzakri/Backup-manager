from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file
from flask import Response, jsonify
from flask_login import login_required, current_user
from app.models import User, Backup, Log
from app import db
from app.backup import run_backup, get_user_backups, delete_backup, clean_old_backups
from app.onedrive import mount_onedrive, unmount_onedrive, get_mount_path
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

# Création du blueprint
bp = Blueprint('main', __name__)

# Formulaires
class AdminUserForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = StringField('Mot de passe', validators=[Length(min=6)])
    is_admin = BooleanField('Administrateur')
    onedrive_folder = StringField('Dossier OneDrive', validators=[Length(max=120)])
    retention_days = IntegerField('Conservation (jours)', validators=[NumberRange(min=1, max=30)], default=2)
    submit = SubmitField('Enregistrer')

class AdminSettingsForm(FlaskForm):
    allow_registration = BooleanField('Autoriser l\'inscription')
    default_retention_days = IntegerField('Conservation par défaut (jours)', validators=[NumberRange(min=1, max=30)], default=2)
    mail_server = StringField('Serveur SMTP', validators=[Optional(), Length(max=120)])
    mail_port = IntegerField('Port SMTP', validators=[Optional(), NumberRange(min=1, max=65535)], default=587)
    mail_use_tls = BooleanField('Utiliser TLS')
    mail_username = StringField('Nom d\'utilisateur SMTP', validators=[Optional(), Length(max=120)])
    mail_password = StringField('Mot de passe SMTP', validators=[Optional(), Length(max=120)])
    mail_default_sender = StringField('Expéditeur par défaut', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Enregistrer')

# Routes
@bp.route('/')
@login_required
def index():
    # Obtenir les sauvegardes de l'utilisateur
    backups = get_user_backups(current_user.id)
    
    # Vérifier si OneDrive est monté
    mount_status = get_mount_path(current_user.username) is not None
    
    # Obtenir les 10 derniers logs de l'utilisateur
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.created_at.desc()).limit(10).all()
    
    return render_template('index.html', 
                          title='Tableau de bord',
                          backups=backups,
                          mount_status=mount_status,
                          logs=logs)

@bp.route('/backup/create', methods=['POST'])
@login_required
def create_backup():
    # Vérifier si OneDrive est monté
    if not get_mount_path(current_user.username):
        flash('OneDrive n\'est pas monté. Veuillez vous reconnecter ou contacter l\'administrateur.', 'danger')
        return redirect(url_for('main.index'))
    
    # Exécuter la sauvegarde
    backup = run_backup(current_user.id)
    
    if backup:
        flash(f'Sauvegarde créée avec succès: {backup.filename}', 'success')
    else:
        flash('Erreur lors de la création de la sauvegarde. Vérifiez les journaux.', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/backup/download/<int:backup_id>')
@login_required
def download_backup(backup_id):
    # Obtenir la sauvegarde
    backup = Backup.query.filter_by(id=backup_id, user_id=current_user.id).first_or_404()
    
    # Vérifier si le fichier existe
    if not os.path.exists(backup.path):
        flash('Le fichier de sauvegarde n\'existe pas.', 'danger')
        return redirect(url_for('main.index'))
    
    # Journalisation du téléchargement
    log = Log(action="backup_download", 
             message=f"Téléchargement de la sauvegarde {backup.filename}",
             user_id=current_user.id)
    db.session.add(log)
    db.session.commit()
    
    # Envoyer le fichier
    return send_file(backup.path, 
                    as_attachment=True, 
                    download_name=backup.filename)

@bp.route('/backup/delete/<int:backup_id>', methods=['POST'])
@login_required
def delete_backup_route(backup_id):
    # Supprimer la sauvegarde
    if delete_backup(backup_id, current_user.id):
        flash('Sauvegarde supprimée avec succès.', 'success')
    else:
        flash('Erreur lors de la suppression de la sauvegarde.', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/backup/clean', methods=['POST'])
@login_required
def clean_backups():
    # Nettoyer les sauvegardes obsolètes
    if clean_old_backups(current_user.id):
        flash('Nettoyage des sauvegardes obsolètes effectué avec succès.', 'success')
    else:
        flash('Erreur lors du nettoyage des sauvegardes.', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/onedrive/mount', methods=['POST'])
@login_required
def mount_onedrive_route():
    # Monter OneDrive
    mount_result = mount_onedrive(current_user.username, current_user.onedrive_folder)
    
    if mount_result:
        flash(f'OneDrive monté avec succès: {mount_result}', 'success')
    else:
        flash('Erreur lors du montage OneDrive. Vérifiez la configuration.', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/onedrive/unmount', methods=['POST'])
@login_required
def unmount_onedrive_route():
    # Démonter OneDrive
    if unmount_onedrive(current_user.username):
        flash('OneDrive démonté avec succès.', 'success')
    else:
        flash('Erreur lors du démontage OneDrive.', 'danger')
    
    return redirect(url_for('main.index'))

@bp.route('/logs')
@login_required
def view_logs():
    # Obtenir tous les logs de l'utilisateur
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.created_at.desc()).all()
    
    return render_template('logs.html', 
                          title='Journaux d\'activité',
                          logs=logs)

# Routes d'administration
@bp.route('/admin')
@login_required
def admin_index():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtenir des statistiques
    user_count = User.query.count()
    backup_count = Backup.query.count()
    
    # Obtenir les 10 derniers logs
    logs = Log.query.order_by(Log.created_at.desc()).limit(20).all()
    
    return render_template('admin/index.html', 
                          title='Administration',
                          user_count=user_count,
                          backup_count=backup_count,
                          logs=logs)

@bp.route('/admin/users')
@login_required
def admin_users():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtenir tous les utilisateurs
    users = User.query.order_by(User.username).all()
    
    return render_template('admin/users.html', 
                          title='Gestion des utilisateurs',
                          users=users)

@bp.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    form = AdminUserForm()
    
    if form.validate_on_submit():
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(username=form.username.data).first():
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return render_template('admin/user_form.html', 
                                  title='Créer un utilisateur',
                                  form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/user_form.html', 
                                  title='Créer un utilisateur',
                                  form=form)
        
        # Créer l'utilisateur
        onedrive_folder = form.onedrive_folder.data or form.username.data
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            is_admin=form.is_admin.data,
            onedrive_folder=onedrive_folder,
            retention_days=form.retention_days.data
        )
        
        db.session.add(user)
        
        # Journalisation de la création
        log = Log(action="admin_user_create", 
                 message=f"Création de l'utilisateur {user.username} par {current_user.username}",
                 user_id=current_user.id)
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Utilisateur {user.username} créé avec succès.', 'success')
        return redirect(url_for('main.admin_users'))
    
    return render_template('admin/user_form.html', 
                          title='Créer un utilisateur',
                          form=form)

@bp.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    form = AdminUserForm()
    
    if request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.is_admin.data = user.is_admin
        form.onedrive_folder.data = user.onedrive_folder
        form.retention_days.data = user.retention_days
    
    if form.validate_on_submit():
        # Vérifier si le nom d'utilisateur est déjà pris
        if form.username.data != user.username and User.query.filter_by(username=form.username.data).first():
            flash('Ce nom d\'utilisateur est déjà pris.', 'danger')
            return render_template('admin/user_form.html', 
                                  title='Modifier un utilisateur',
                                  form=form,
                                  user=user)
        
        # Vérifier si l'email est déjà pris
        if form.email.data != user.email and User.query.filter_by(email=form.email.data).first():
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('admin/user_form.html', 
                                  title='Modifier un utilisateur',
                                  form=form,
                                  user=user)
        
        # Mettre à jour l'utilisateur
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.onedrive_folder = form.onedrive_folder.data
        user.retention_days = form.retention_days.data
        
        # Si un nouveau mot de passe est fourni, le mettre à jour
        if form.password.data:
            from app import bcrypt
            user.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Journalisation de la modification
        log = Log(action="admin_user_edit", 
                 message=f"Modification de l'utilisateur {user.username} par {current_user.username}",
                 user_id=current_user.id)
        db.session.add(log)
        
        db.session.commit()
        
        flash(f'Utilisateur {user.username} modifié avec succès.', 'success')
        return redirect(url_for('main.admin_users'))
    
    return render_template('admin/user_form.html', 
                          title='Modifier un utilisateur',
                          form=form,
                          user=user)

@bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    
    # Empêcher la suppression de son propre compte
    if user.id == current_user.id:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('main.admin_users'))
    
    # Supprimer les sauvegardes associées
    backups = Backup.query.filter_by(user_id=user.id).all()
    for backup in backups:
        try:
            if os.path.exists(backup.path):
                os.remove(backup.path)
            db.session.delete(backup)
        except Exception as e:
            current_app.logger.error(f"Erreur lors de la suppression de la sauvegarde {backup.filename}: {str(e)}")
    
    # Supprimer les logs associés
    logs = Log.query.filter_by(user_id=user.id).all()
    for log in logs:
        db.session.delete(log)
    
    # Journalisation de la suppression
    log = Log(action="admin_user_delete", 
             message=f"Suppression de l'utilisateur {user.username} par {current_user.username}",
             user_id=current_user.id)
    db.session.add(log)
    
    # Démonter OneDrive si nécessaire
    try:
        unmount_onedrive(user.username)
    except Exception as e:
        current_app.logger.error(f"Erreur lors du démontage OneDrive pour {user.username}: {str(e)}")
    
    # Supprimer l'utilisateur
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Utilisateur {username} supprimé avec succès.', 'success')
    return redirect(url_for('main.admin_users'))

@bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    form = AdminSettingsForm()
    
    if request.method == 'GET':
        form.allow_registration.data = current_app.config.get('ALLOW_REGISTRATION', True)
        form.default_retention_days.data = current_app.config.get('DEFAULT_RETENTION_DAYS', 2)
        form.mail_server.data = current_app.config.get('MAIL_SERVER', '')
        form.mail_port.data = current_app.config.get('MAIL_PORT', 587)
        form.mail_use_tls.data = current_app.config.get('MAIL_USE_TLS', True)
        form.mail_username.data = current_app.config.get('MAIL_USERNAME', '')
        form.mail_password.data = current_app.config.get('MAIL_PASSWORD', '')
        form.mail_default_sender.data = current_app.config.get('MAIL_DEFAULT_SENDER', '')
    
    if form.validate_on_submit():
        # Mettre à jour les paramètres
        current_app.config['ALLOW_REGISTRATION'] = form.allow_registration.data
        current_app.config['DEFAULT_RETENTION_DAYS'] = form.default_retention_days.data
        current_app.config['MAIL_SERVER'] = form.mail_server.data
        current_app.config['MAIL_PORT'] = form.mail_port.data
        current_app.config['MAIL_USE_TLS'] = form.mail_use_tls.data
        current_app.config['MAIL_USERNAME'] = form.mail_username.data
        current_app.config['MAIL_PASSWORD'] = form.mail_password.data
        current_app.config['MAIL_DEFAULT_SENDER'] = form.mail_default_sender.data
        
        # Réinitialiser l'extension mail avec les nouveaux paramètres
        from app import mail
        mail.init_app(current_app)
        
        # Journalisation de la modification
        log = Log(action="admin_settings_update", 
                 message=f"Mise à jour des paramètres par {current_user.username}",
                 user_id=current_user.id)
        db.session.add(log)
        db.session.commit()
        
        flash('Paramètres mis à jour avec succès.', 'success')
        return redirect(url_for('main.admin_index'))
    
    return render_template('admin/settings.html', 
                          title='Paramètres',
                          form=form)

@bp.route('/admin/logs')
@login_required
def admin_logs():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtenir tous les logs
    logs = Log.query.order_by(Log.created_at.desc()).all()
    
    return render_template('admin/logs.html', 
                          title='Journaux d\'activité',
                          logs=logs)

@bp.route('/admin/backups')
@login_required
def admin_backups():
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtenir toutes les sauvegardes
    backups = Backup.query.order_by(Backup.created_at.desc()).all()
    
    return render_template('admin/backups.html', 
                          title='Sauvegardes',
                          backups=backups)

@bp.route('/admin/backup/delete/<int:backup_id>', methods=['POST'])
@login_required
def admin_delete_backup(backup_id):
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Supprimer la sauvegarde
    if delete_backup(backup_id):
        flash('Sauvegarde supprimée avec succès.', 'success')
    else:
        flash('Erreur lors de la suppression de la sauvegarde.', 'danger')
    
    return redirect(url_for('main.admin_backups'))

@bp.route('/admin/backup/download/<int:backup_id>')
@login_required
def admin_download_backup(backup_id):
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    # Obtenir la sauvegarde
    backup = Backup.query.get_or_404(backup_id)
    
    # Vérifier si le fichier existe
    if not os.path.exists(backup.path):
        flash('Le fichier de sauvegarde n\'existe pas.', 'danger')
        return redirect(url_for('main.admin_backups'))
    
    # Journalisation du téléchargement
    log = Log(action="admin_backup_download", 
             message=f"Téléchargement administratif de la sauvegarde {backup.filename}",
             user_id=current_user.id)
    db.session.add(log)
    db.session.commit()
    
    # Envoyer le fichier
    return send_file(backup.path, 
                    as_attachment=True, 
                    download_name=backup.filename)

@bp.route('/admin/backup/create/<int:user_id>', methods=['POST'])
@login_required
def admin_create_backup(user_id):
    # Vérifier si l'utilisateur est administrateur
    if not current_user.is_admin:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('main.index'))
    
    user = User.query.get_or_404(user_id)
    
    # Vérifier si OneDrive est monté
    if not get_mount_path(user.username):
        # Essayer de monter automatiquement
        mount_result = mount_onedrive(user.username, user.onedrive_folder)
        if not mount_result:
            flash(f'OneDrive n\'est pas monté pour {user.username}. Veuillez monter manuellement.', 'danger')
            return redirect(url_for('main.admin_users'))
    
    # Exécuter la sauvegarde
    backup = run_backup(user.id)
    
    if backup:
        flash(f'Sauvegarde créée avec succès pour {user.username}: {backup.filename}', 'success')
    else:
        flash(f'Erreur lors de la création de la sauvegarde pour {user.username}.', 'danger')
    
    return redirect(url_for('main.admin_users'))

@bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', title='Page non trouvée'), 404

@bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', title='Erreur serveur'), 500

@bp.app_errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html', title='Accès interdit'), 403
