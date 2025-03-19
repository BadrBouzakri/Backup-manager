from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange
from app.models import User, Log
from app import db
import os
from app.onedrive import mount_onedrive, unmount_onedrive
from flask import current_app


# Création du blueprint
bp = Blueprint('auth', __name__)

# Formulaires
class LoginForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired()])
    password = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de moi')
    submit = SubmitField('Se connecter')

class RegistrationForm(FlaskForm):
    username = StringField('Nom d\'utilisateur', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmer le mot de passe', validators=[DataRequired(), EqualTo('password')])
    onedrive_folder = StringField('Dossier OneDrive', validators=[Length(max=120)])
    retention_days = IntegerField('Conservation (jours)', validators=[NumberRange(min=1, max=30)], default=2)
    submit = SubmitField('S\'inscrire')
    
    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Cet email est déjà utilisé.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Ancien mot de passe', validators=[DataRequired()])
    password = PasswordField('Nouveau mot de passe', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmer le nouveau mot de passe', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Changer le mot de passe')

class SettingsForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    onedrive_folder = StringField('Dossier OneDrive', validators=[Length(max=120)])
    retention_days = IntegerField('Conservation (jours)', validators=[NumberRange(min=1, max=30)])
    submit = SubmitField('Enregistrer')

# Routes
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data):
            flash('Nom d\'utilisateur ou mot de passe incorrect.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Journalisation de la connexion
        log = Log(action="login", message=f"Connexion de l'utilisateur {user.username}", user_id=user.id)
        db.session.add(log)
        db.session.commit()
        
        # Montage du dossier OneDrive de l'utilisateur
        try:
            mount_result = mount_onedrive(user.username, user.onedrive_folder)
            if mount_result:
                flash(f'OneDrive monté avec succès: {mount_result}', 'success')
            else:
                flash('Erreur lors du montage OneDrive. Vérifiez la configuration.', 'warning')
        except Exception as e:
            flash(f'Erreur de montage OneDrive: {str(e)}', 'danger')
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Connexion', form=form)

@bp.route('/logout')
@login_required
def logout():
    # Démontage du dossier OneDrive avant la déconnexion
    try:
        unmount_onedrive(current_user.username)
    except Exception as e:
        flash(f'Erreur lors du démontage OneDrive: {str(e)}', 'warning')
    
    # Journalisation de la déconnexion
    log = Log(action="logout", message=f"Déconnexion de l'utilisateur {current_user.username}", user_id=current_user.id)
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if not current_app.config.get('ALLOW_REGISTRATION', True):
        flash('L\'inscription est désactivée.', 'warning')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        onedrive_folder = form.onedrive_folder.data or form.username.data
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            onedrive_folder=onedrive_folder,
            retention_days=form.retention_days.data
        )
        
        db.session.add(user)
        
        # Journalisation de l'inscription
        log = Log(action="register", message=f"Inscription de l'utilisateur {user.username}")
        db.session.add(log)
        
        db.session.commit()
        
        flash('Félicitations, vous êtes maintenant inscrit!', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Inscription', form=form)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm()
    if request.method == 'GET':
        form.email.data = current_user.email
        form.onedrive_folder.data = current_user.onedrive_folder
        form.retention_days.data = current_user.retention_days
    
    if form.validate_on_submit():
        if current_user.email != form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('Cet email est déjà utilisé.', 'danger')
        else:
            current_user.email = form.email.data
            current_user.retention_days = form.retention_days.data
            
            # Si le dossier OneDrive a changé, nous devons démonter puis remonter
            if current_user.onedrive_folder != form.onedrive_folder.data:
                try:
                    unmount_onedrive(current_user.username)
                    current_user.onedrive_folder = form.onedrive_folder.data
                    mount_result = mount_onedrive(current_user.username, current_user.onedrive_folder)
                    if mount_result:
                        flash(f'OneDrive monté avec succès: {mount_result}', 'success')
                    else:
                        flash('Erreur lors du montage OneDrive. Vérifiez la configuration.', 'warning')
                except Exception as e:
                    flash(f'Erreur de montage OneDrive: {str(e)}', 'danger')
            
            # Journalisation de la modification
            log = Log(action="settings_update", 
                      message=f"Mise à jour des paramètres pour {current_user.username}", 
                      user_id=current_user.id)
            db.session.add(log)
            
            db.session.commit()
            flash('Vos paramètres ont été mis à jour.', 'success')
            return redirect(url_for('main.index'))
    
    return render_template('auth/settings.html', title='Paramètres', form=form)

@bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.verify_password(form.old_password.data):
            flash('Mot de passe actuel incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        
        from app import bcrypt
        current_user.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Journalisation du changement de mot de passe
        log = Log(action="password_change", 
                  message=f"Changement de mot de passe pour {current_user.username}", 
                  user_id=current_user.id)
        db.session.add(log)
        
        db.session.commit()
        flash('Votre mot de passe a été modifié.', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('auth/change_password.html', title='Changer le mot de passe', form=form)
