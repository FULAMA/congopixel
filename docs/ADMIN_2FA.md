# Double authentification de l'admin

Activation (ordre important, pour ne pas se bloquer) :
1. Déployer le code avec ADMIN_2FA absent ou à False.
2. Sur le serveur : `python manage.py setup_2fa NOM_DU_COMPTE` (lancer seule), scanner le QR, saisir le code, noter les 8 codes de secours sur papier.
3. Ajouter `ADMIN_2FA=True` au .env, puis Reload.
4. Tester la connexion dans une fenêtre privée (mot de passe + code à 6 chiffres).
Chaque compte équipe doit avoir son propre appareil (setup_2fa NOM).

Téléphone perdu : utiliser un code de secours (à usage unique). Sinon, depuis la console du serveur : `python manage.py reset_2fa NOM`, puis `python manage.py setup_2fa NOM`.
Urgence : mettre ADMIN_2FA=False dans le .env et Reload retire l'obligation du code (à remettre à True ensuite).
L'heure du téléphone doit être automatique : un code est valable environ 30 secondes.