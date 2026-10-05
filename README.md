# Tracker d'offres de stage

Un robot interroge les pages carrières toutes les ~3 min, filtre les offres (stage + sujet + lieu)
et publie le résultat sur ton site. Garde le site ouvert dans un onglet : il se met à jour tout seul
chaque minute, affiche un bandeau, joue un son et envoie une notification du navigateur à chaque nouvelle offre.

## Mise en route (15 min)

1. **Repo public sur GitHub** (nécessaire : Actions est illimité en public, plafonné à 2000 min/mois en privé).
   Il ne contient aucun secret : seulement ta liste d'entreprises et les offres publiques.
2. Pousse ce dossier dans le repo, puis **Settings > Pages > Source : Deploy from a branch > main /docs**.
   Ton site sera sur `https://<ton-user>.github.io/<repo>/`.
3. **Telegram (facultatif)** : à faire seulement si tu veux aussi les alertes quand le site est fermé. écris à @BotFather (`/newbot`) pour obtenir le token. Envoie un message à ton bot,
   puis ouvre `https://api.telegram.org/bot<TOKEN>/getUpdates` pour lire ton `chat.id`.
4. *(facultatif, avec Telegram)* **Settings > Secrets and variables > Actions** : crée `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`.
   Sans ces secrets, le robot fonctionne normalement, simplement sans Telegram.
5. **Actions > scan > Run workflow** une première fois. Cette passe initialise la base sans envoyer d'alertes.
6. **Rythme de 3 min** : le cron natif de GitHub est lent et irrégulier. Sur cron-job.org (gratuit),
   crée un job toutes les 3 min :
   - URL : `https://api.github.com/repos/<user>/<repo>/actions/workflows/scan.yml/dispatches`
   - Méthode : POST, corps : `{"ref":"main"}`
   - En-têtes : `Authorization: Bearer <PAT>`, `Accept: application/vnd.github+json`, `Content-Type: application/json`
   - Le PAT est un *fine-grained token* limité à ce repo, permission **Actions : Read and write**.

## Sources branchées (32)

**Vérifiées** (structure lue sur le site) : BNP Paribas, Société Générale, Crédit Agricole
(CA CIB, Amundi, Indosuez, CACEIS, LCL), Citi, Barclays, Rothschild & Co, Ardian, Houlihan Lokey.

**À tester** (identifiants connus, jamais appelés depuis ici) : Deutsche Bank, Santander,
Lombard Odier, Julius Baer, BlackRock, Fidelity International, State Street, Invesco, Blackstone,
Apollo, JP Morgan, Goldman Sachs, Schroders, Bank of America, Lazard, Morgan Stanley, Evercore,
Point72, Man Group, Marshall Wace, Bridgewater, EQT, TPG, Apax.

**Non branchées** (100 % JavaScript) : Natixis/BPCE, HSBC, UBS, Edmond de Rothschild, Pictet, Oddo BHF.

**Avant le premier lancement**, teste tout depuis ton ordi :

```
pip install -r requirements.txt
python -m tracker.check config ""      # teste les 32 sources d'un coup
```

Une source qui affiche une erreur ou 0 offre : commente-la dans `config.yaml`, ou envoie la sortie
pour correction. Une source ajoutée plus tard est initialisée en silence (pas d'avalanche d'alertes).

## Ajouter une entreprise (`config.yaml`)

- Site dont les offres sont des liens visibles dans le HTML : `html_links` avec l'URL de la liste
  et un morceau d'URL commun à toutes les offres (`link_contains`). C'est le cas le plus fréquent.

- Plateformes standard (Greenhouse, Lever, SmartRecruiters, Workday) : 2 lignes.
- Portails maison (la plupart des banques) : `generic_json` avec l'endpoint trouvé dans l'onglet Réseau (F12),
  ou `generic_html` avec des sélecteurs CSS.
- Teste toujours avant : `python -m tracker.check config "NomEntreprise"`.

## Alertes sur le site

- Clique sur **Activer les alertes** une fois : le navigateur te demandera l'autorisation.
- Les notifications arrivent tant que l'onglet est ouvert, même en arrière-plan. Onglet fermé = pas d'alerte
  (c'est la seule chose que Telegram fait en plus).
- Le titre de l'onglet affiche le nombre de nouveautés, par exemple « (3) Offres de stage ».
- Délai total entre la publication d'une offre et l'alerte : environ 3 à 5 min
  (passage du robot, puis ~1 min de mise à jour de GitHub Pages, puis la vérification du site chaque minute).

## Limites à connaître

- Le suivi des statuts (postulé, relancé...) est enregistré dans ton navigateur (localStorage), pas dans le repo.
- Une source qui échoue 3 fois de suite déclenche une alerte Telegram.
- Les sites protégés anti-bot (Cloudflare, Datadome) ne sont pas fiables en simple requête HTTP.
