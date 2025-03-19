#!/bin/bash
set -e

# Attendre que la base de données soit prête
echo "Waiting for database to be ready..."
until PGPASSWORD=${DB_PASSWORD} psql -h db -U ${DB_USER} -d ${DB_NAME} -c '\q'; do
  >&2 echo "Database is unavailable - sleeping"
  sleep 1
done

# Initialiser ou mettre à jour la base de données
echo "Database is up - initializing or upgrading schema"
python -c "from app import create_app, db; app = create_app('production'); app.app_context().push(); db.create_all()"

# Créer un utilisateur administrateur si nécessaire
echo "Checking for admin user..."
python -c "
from app import create_app, db
from app.models import User
app = create_app('production')
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        from app import bcrypt
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=bcrypt.generate_password_hash('admin').decode('utf-8'),
            is_admin=True,
            retention_days=2
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created')
    else:
        print('Admin user already exists')
"

# Exécuter la commande fournie
exec "$@"
