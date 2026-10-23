# Tests de CongoPixel

Lancer tout : `python manage.py test`
Lancer une famille :
- Unitaires : `python manage.py test core.test_units`
- Sécurité : `python manage.py test core.test_security -v 2`
- Intégration : `python manage.py test core.test_integration`
- Parcours fonctionnels : `python manage.py test core.test_functional`
- Argent, stock, comptes : `python manage.py test orders payments accounts catalog`

Vérifications de configuration avant une mise en ligne (avec le .env de production) :
`python manage.py check --deploy`
`python manage.py security_audit`

Ce que les tests ne couvrent pas : test de charge, test dans un vrai navigateur (JavaScript), audit externe, protections de l'hébergeur.
Avant un lancement important, prévoir un test à la main sur téléphone avec la connexion mobile.