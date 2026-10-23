# Modèle de menaces de CongoPixel

Actifs à protéger : données clients (nom, téléphone, adresse), accès à l'administration, intégrité des commandes et des paiements, stock, disponibilité du site, secrets (.env, clés), réputation.

| Menace | Défenses en place | Tests | Risque restant |
|---|---|---|---|
| Vol d'accès admin (force brute, mot de passe faible) | URL admin secrète, blocage après 10 échecs en 15 min, validation des mots de passe, journal des échecs | test_admin_login_is_throttled, test_weak_passwords... | Hameçonnage ; pas de double authentification |
| Escalade de privilèges | Formulaire d'inscription restreint, groupes à droits limités | test_registration_cannot_grant_privileges, test_order_manager_group_is_limited | Erreur humaine (super-utilisateur donné par erreur) : security_audit |
| Accès aux commandes d'autrui | Accès par session ou compte propriétaire, réponse 404 | test_orders_are_isolated_between_sessions | Partage du lien de session |
| XSS (script injecté) | Échappement automatique, CSP sans script inline, JSON-LD échappé | test_user_controlled_text_is_escaped, test_pages_have_no_inline_executable_scripts | Admin hors CSP : comptes équipe de confiance uniquement |
| CSRF | Jeton CSRF Django | test_post_endpoints_require_csrf_token | Faible |
| Injection SQL | ORM Django | test_sql_injection_attempts_are_harmless | Faible |
| Fraude au paiement (faux ID, ID réutilisé) | Contrainte d'unicité, vérification humaine du montant et de l'ID dans l'application Mobile Money | tests payments | Validation humaine indispensable tant qu'il n'y a pas d'API |
| Double soumission, rejeu | Clé d'idempotence, confirmation idempotente, refus de confirmer une commande annulée | tests payments | Faible |
| Survente, stock bloqué par des robots | Verrou et recalage du stock, expiration à 24 h, limites par session | test_checkout_detects_stock_change..., tests robustness | Limites contournables (cookies) : ajouter un CAPTCHA ou un pare-feu si abus |
| Manipulation des prix et des statuts | Tout est recalculé côté serveur | test_price_and_status_tampering_is_ignored | Faible |
| Fichiers piégés (upload) | Contrôle Pillow, ré-encodage WebP | test_uploads_must_be_real_images | Faible (admin uniquement) |
| Fuite via les journaux | Pas de noms ni téléphones, identifiants masqués | test_checkout_logs_contain_no_personal_data | Faible |
| Injection de formules Excel (export CSV) | Cellules neutralisées | test_csv_cell_sanitizer | Faible |
| Redirection ouverte, fixation de session | Contrôle du paramètre next, rotation de session | test_no_open_redirect..., test_session_key_rotates_on_login | Faible |
| Secrets exposés | .env hors Git, contrôles check --deploy | test_hardening_check_* | Fuite via GitHub ou un poste infecté : changer les clés (voir INCIDENT_RESPONSE.md) |
| Déni de service | Limites de débit, expiration | partiels | Élevé sur l'hébergement gratuit ; protection réseau (type Cloudflare) à prévoir avec un domaine |
| Dépendances vulnérables | requirements.txt figé | aucun | Vérifier chaque mois les mises à jour de sécurité de Django |

Limites assumées : verrouillage temporaire d'un identifiant par un attaquant (déni de service ciblé), enregistrement qui révèle si un numéro est déjà inscrit.