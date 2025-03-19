#!/bin/bash

# Script de sauvegarde pour Backup-manager
# Usage: backup.sh [chemin_source] [chemin_destination] [nom_utilisateur]

# Vérification des arguments
if [ "$#" -lt 3 ]; then
    echo "Usage: $0 [chemin_source] [chemin_destination] [nom_utilisateur]"
    exit 1
fi

# Récupération des arguments
SOURCE_PATH="$1"
DEST_PATH="$2"
USERNAME="$3"

# Vérification de l'existence du chemin source
if [ ! -d "$SOURCE_PATH" ]; then
    echo "Erreur: Le chemin source '$SOURCE_PATH' n'existe pas."
    exit 1
fi

# Vérification et création du dossier de destination si nécessaire
if [ ! -d "$DEST_PATH" ]; then
    mkdir -p "$DEST_PATH"
    if [ $? -ne 0 ]; then
        echo "Erreur: Impossible de créer le dossier de destination '$DEST_PATH'."
        exit 1
    fi
fi

# Création d'un nom de fichier unique avec horodatage
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILENAME="${USERNAME}_backup_${TIMESTAMP}.tar.gz"
BACKUP_PATH="${DEST_PATH}/${BACKUP_FILENAME}"

# Création de l'archive compressée
echo "Création de la sauvegarde à partir de '$SOURCE_PATH' vers '$BACKUP_PATH'..."
tar -czf "$BACKUP_PATH" -C "$(dirname "$SOURCE_PATH")" "$(basename "$SOURCE_PATH")"

# Vérification du résultat
if [ $? -eq 0 ]; then
    echo "Sauvegarde réussie: $BACKUP_PATH"
    # Afficher la taille du fichier de sauvegarde
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo "Taille de la sauvegarde: $BACKUP_SIZE"
    exit 0
else
    echo "Erreur lors de la création de la sauvegarde."
    exit 1
fi
