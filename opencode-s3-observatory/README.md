# Conversation Observatory

Application locale qui publie les événements visibles de Pi et OpenCode dans
Redpanda, les diffuse en direct avec Arroyo/SSE, les conserve dans Apache
Iceberg sur SeaweedFS/S3 et les explore avec Streamlit.

## Demarrage rapide

Depuis ce dossier :

```bash
docker compose up -d --build
```

Ouvrir ensuite :

- Dashboard HTML temps réel : `http://localhost:8503`
- Dashboard Streamlit historique : `http://localhost:8501`
- Interface Arroyo : `http://localhost:8510`
- Redpanda REST Proxy : `http://localhost:18082`
- Catalogue Iceberg : `http://localhost:8181`
- Documentation : `http://localhost:8502`

Les identifiants S3 sont uniquement destines a la demonstration locale :
`admin` / `bigdata-local-secret`, bucket `bigdata`, region `us-east-1`.

## Arborescence

```text
app/                         Dashboard Streamlit
live-dashboard/              Dashboard HTML alimenté en SSE
config/arroyo-live.sql       Pipeline SQL Arroyo
scripts/                     Publication, ingestion et provisionnement
opencode/                    Plugin d'export OpenCode
docs/                        Site Docsify et documentation Markdown
spark/                       Promotion Bronze vers Silver et tables Gold
docker-compose.yml           Services du pipeline local
```

## Commandes courantes

```bash
# Voir les conteneurs et leurs journaux
docker compose ps
docker compose logs -f dashboard
docker compose logs -f arroyo
docker compose logs -f documentation

# Installer l'extension pi en temps réel
chmod +x scripts/install-pi-extension.sh
./scripts/install-pi-extension.sh

# Puis lancer ou recharger pi
pi

# Promouvoir Bronze vers Silver et actualiser les tables Gold
docker compose --profile spark run --build --rm spark-batch

# Arreter les conteneurs sans supprimer les donnees S3
docker compose down
```

## Documentation

- [Export pi vers Redpanda](docs/operations/pi.md)
- [Architecture de la chaine de donnees](docs/guide/architecture.md)
- [Gouvernance des donnees et garanties ACID](docs/guide/data-governance.md)
- [Index de la documentation](docs/README.md)

L'extension pi publie directement les prompts, reponses, appels d'outils et
sorties visibles dans Redpanda. Les blocs thinking ne sont pas publies. Redpanda, S3 et les
logs doivent rester locaux et prives, car un prompt ou une sortie de commande
peut contenir un secret.

## Vues du dashboard

Le projet propose deux interfaces complémentaires :

- `Dashboard HTML temps réel` (`:8503`) : réponses, tokens et coûts reçus par SSE directement depuis Arroyo, sans polling ni rechargement.
- `Dashboard Streamlit` (`:8501`) : historique Iceberg, discussions, statistiques, requêtes Spark et comparateur technique.

Le dashboard Streamlit propose trois vues explicites :

- `Vue d'ensemble` : volumes, coûts, tokens, comparaison historique des modèles et des harnais, activité dans le temps et outils utilisés.
- `Comparateur technique` : rapprochement automatique des conversations CLI Pi et OpenCode qui utilisent le même prompt et le même modèle.
- `Fil de discussion` : prompts, reponses et operations d'une session dans
  l'ordre chronologique.
- `Requetes Spark` : requetes SQL de lecture executees par Spark sur Iceberg.

Le bouton du `Fil de discussion` ouvre le flux interactif de la session.

## Traitement batch Spark

Le dashboard lit Bronze pour afficher les nouveaux messages immediatement et
les deduplique avec DuckDB. Le service optionnel `spark-batch` promeut
`opencode.events_bronze` vers `opencode.events`, puis ecrit les tables Iceberg
`opencode.session_summary` et `opencode.tool_summary`. Spark reste reserve aux
traitements analytiques et aux requetes SQL.

## Requetes Spark

L'onglet `Requetes Spark` execute des requetes SQL de lecture sur la vue
`events`, alimentee par un snapshot Iceberg de `opencode.events`. Les requetes
`SELECT`, `WITH`, `SHOW`, `DESCRIBE` et `EXPLAIN` sont acceptees et limitees a
500 lignes. Les noms `opencode.events`, `opencode.session_summary` et
`opencode.tool_summary` sont automatiquement traduits vers le catalogue Spark.
