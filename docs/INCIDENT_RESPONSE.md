# Réponse aux incidents de CongoPixel

Principes : garder son calme, noter l'heure, ne rien supprimer des journaux, faire une sauvegarde avant toute action lourde.
Console PythonAnywhere : `cd ~/congopixel && workon congopixel-venv`
Journaux : onglet Web, section Log files (erreurs et accès).

## 0. Toujours
1. `python manage.py backup_db` (copie de sécurité)
2. `python manage.py security_audit` (état des lieux)

## A. Compte administrateur compromis ou suspect
1. Déconnecter tout le monde : `python manage.py revoke_sessions`
2. Changer le mot de passe de chaque compte équipe : `python manage.py changepassword NOM`
3. Désactiver un compte douteux : `python manage.py revoke_sessions --user NOM --deactivate`
4. Changer ADMIN_URL dans le .env (`nano .env`), puis Reload dans l'onglet Web
5. Changer SECRET_KEY : générer avec `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`, remplacer dans .env, Reload
6. Relire les commandes et paiements récents dans l'admin ; chercher les actions inhabituelles dans les journaux
7. Changer aussi les mots de passe PythonAnywhere et GitHub ; activer la double authentification sur les deux

## B. Fraude au paiement (faux ID, montant incorrect)
1. Ne pas confirmer ; utiliser Rejeter ; écrire au client sur WhatsApp
2. Comparer ID, montant et numéro dans l'application Orange Money ou M-Pesa
3. Si déjà confirmé et livré : conserver les preuves et contacter l'opérateur ; noter le numéro et la zone

## C. Vague de commandes fantômes (robots)
1. `python manage.py expire_orders --hours 1` pour libérer le stock
2. Baisser temporairement UNPAID_ORDER_EXPIRY_HOURS dans le .env, Reload
3. Si cela continue : mettre un nom de domaine derrière un service de protection (CAPTCHA, pare-feu) et durcir les limites

## D. Paiement confirmé sur une commande annulée
Le site avertit (message orange, ligne « remboursement » dans security_audit). Rembourser le client, ou recréer la commande et remettre le stock à jour.

## E. Fuite de clé, de jeton ou du .env
1. Révoquer le jeton GitHub concerné ; changer SECRET_KEY et tous les mots de passe
2. `python manage.py revoke_sessions`
3. Vérifier que .env, db.sqlite3 et backups/ ne sont pas dans Git : `git ls-files`

## F. Site modifié ou code suspect
1. `git status` et `git diff` pour voir les changements non voulus
2. Restaurer : `git checkout .` puis `git pull`
3. Changer tous les mots de passe (voir A), vérifier les comptes équipe

## G. Base de données perdue ou corrompue
1. Repérer la dernière sauvegarde dans `backups/`
2. `cp backups/db-AAAAMMJJ-HHMMSS.sqlite3 db.sqlite3` puis `python manage.py migrate`, puis Reload
3. Reconstituer les commandes manquantes depuis WhatsApp et l'historique Orange Money / M-Pesa

## H. Données de clients exposées
1. Contenir (étapes A et E), puis évaluer ce qui a été vu (noms, téléphones, adresses)
2. Prévenir les clients concernés par WhatsApp, sans minimiser
3. Se renseigner sur les obligations légales locales

## Après chaque incident
Écrire ce qui s'est passé, corriger la cause, ajouter un test pour que ça ne se reproduise pas.

## Hygiène régulière
- Chaque semaine : backup_db puis téléchargement du fichier, security_audit
- Chaque mois : prolonger le compte gratuit, vérifier les mises à jour de sécurité de Django, relire les journaux
- Chaque trimestre : changer les mots de passe, revoir les comptes équipe