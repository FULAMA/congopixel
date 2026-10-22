# Mise en ligne de CongoPixel sur PythonAnywhere (compte gratuit)

Remplace rien : ton nom PythonAnywhere (FULAMA) et ton compte GitHub (https://github.com/FULAMA/congopixel) sont déjà dans ce guide.

## 1. Envoyer le code sur GitHub (une fois, sur ton PC)
1. Sur github.com, crée un dépôt PRIVÉ nommé `congopixel` (sans README).
2. Dans PowerShell :

    Set-Location C:\Dev\CongoPixel
    git remote add origin https://github.com/FULAMA/congopixel.git
    git branch -M main
    git push -u origin main

Le `.env`, la base, les photos, les sauvegardes et `.env.production` ne partent pas dans Git.

## 2. Préparer PythonAnywhere
1. Crée le compte gratuit (nom d'utilisateur : FULAMA). Ton site sera https://fulama.pythonanywhere.com
2. Onglet Consoles : ouvre une console Bash.
3. Récupère le code (si le dépôt est privé, PythonAnywhere te demande un identifiant : utilise ton compte GitHub et, comme mot de passe, un jeton d'accès personnel en lecture seule) :

    git clone https://github.com/FULAMA/congopixel.git
    cd congopixel

4. Vérifie les versions de Python disponibles, puis crée l'environnement virtuel avec la plus récente (3.12 ou plus ; remplace 3.13 si besoin) :

    ls /usr/bin/python3*
    mkvirtualenv congopixel-venv --python=python3.13
    pip install -r requirements.txt

## 3. Configuration de production
1. Sur ton PC, ouvre `.env.production` (Bloc-notes) et copie tout son contenu.
2. Dans la console PythonAnywhere : `nano .env`, colle le contenu, puis Ctrl+O, Entrée, Ctrl+X.
3. Note l'adresse secrète de l'admin (ligne ADMIN_URL). Ton admin sera https://fulama.pythonanywhere.com/ + cette valeur. Ne la partage qu'avec ton équipe.

## 4. Base de données et fichiers statiques

    python manage.py migrate
    python manage.py collectstatic --noinput
    python manage.py createsuperuser
    python manage.py seed_initial
    python manage.py setup_groups

Pour createsuperuser, choisis un mot de passe long (12 caractères ou plus) et DIFFÉRENT de celui de ton PC.

## 5. Onglet Web
1. Add a new web app, puis Manual configuration, puis la même version de Python qu'à l'étape 2.
2. Virtualenv : `/home/FULAMA/.virtualenvs/congopixel-venv`
3. Source code : `/home/FULAMA/congopixel`
4. Clique sur le lien du fichier WSGI et remplace TOUT son contenu par :

    import os
    import sys

    path = "/home/FULAMA/congopixel"
    if path not in sys.path:
        sys.path.insert(0, path)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()

5. Section Static files, ajoute deux lignes :
   - URL `/static/` vers `/home/FULAMA/congopixel/staticfiles`
   - URL `/media/` vers `/home/FULAMA/congopixel/media`
6. Active "Force HTTPS".
7. Clique sur le gros bouton vert Reload.

## 6. Premiers réglages (dans l'admin de production)
1. Core, Paramètres du site : taux USD/CDF, numéro WhatsApp (243XXXXXXXXX), numéros Orange Money et M-Pesa.
2. Orders, Zones de livraison : frais de chaque zone.
3. Catalog : crée tes vrais produits, avec photos et variantes avec stock.
4. Teste une commande complète avec un faux ID, puis annule-la (le stock revient).

## 7. Entretien
- Prolongation : le compte gratuit expire au bout d'un mois. Chaque mois, onglet Web, clique sur le bouton de prolongation.
- Sauvegarde (chaque semaine) : console Bash, `cd ~/congopixel && python manage.py backup_db`, puis télécharge le fichier depuis l'onglet Files (dossier `backups`). Les photos sont dans le dossier `media`.
- Mise à jour du site : sur ton PC, commit et `git push`. Dans la console PythonAnywhere :

    cd ~/congopixel
    git pull
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py collectstatic --noinput

  puis Reload dans l'onglet Web.

## 8. Reprendre tes produits de test (facultatif)
Le plus simple : saisis tes vrais produits directement dans l'admin de production.