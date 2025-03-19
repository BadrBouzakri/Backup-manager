FROM python:3.10-slim

# Installer rclone et autres dépendances
RUN apt-get update && apt-get install -y \
    fuse \
    curl \
    wget \
    unzip \
    && curl https://rclone.org/install.sh | bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m appuser
WORKDIR /app

# Copier les fichiers requis
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste de l'application
COPY . .

# Créer les répertoires nécessaires
RUN mkdir -p instance storage/backups storage/mounts logs \
    && chown -R appuser:appuser /app

# Autoriser l'utilisateur à utiliser fuse
RUN chmod u+s /bin/fusermount

# Exposer le port
EXPOSE 5000

# Utiliser l'utilisateur non-root
USER appuser

# Commande de démarrage
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
