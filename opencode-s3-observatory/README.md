# Conversation Observatory

Application locale qui publie les evenements visibles des sessions pi dans Redpanda,
les conserve dans Apache Iceberg sur SeaweedFS/S3 et les explore avec Streamlit.

## Demarrage rapide

Depuis ce dossier :

```bash
docker compose up -d --build
```

Ouvrir ensuite :

- Dashboard : `http://localhost:8501`
- Redpanda REST Proxy : `http://localhost:18082`
- Catalogue Iceberg : `http://localhost:8181`
- Documentation : `http://localhost:8502`

Les identifiants S3 sont uniquement destines a la demonstration locale :
`admin` / `bigdata-local-secret`, bucket `bigdata`, region `us-east-1`.

## Arborescence

```text
app/                         Dashboard Streamlit
scripts/                     Publication pi et ingestion Iceberg
docs/                        Site Docsify et documentation Markdown
spark/                       Promotion Bronze vers Silver et tables Gold
docker-compose.yml           Services du pipeline local
```

## Commandes courantes

```bash
# Voir les conteneurs et leurs journaux
docker compose ps
docker compose logs -f dashboard
docker compose logs -f documentation

# Lancer pi depuis la racine du projet : l'extension est chargee automatiquement
cd ..
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

Le dashboard propose trois vues explicites :

- `Vue globale` : volumes, couts, tokens, modeles et outils utilises.
- `Fil de discussion` : prompts, reponses et operations d'une session dans
  l'ordre chronologique.
- `Requetes Spark` : requetes SQL de lecture executees par Spark sur Iceberg.

Le bouton du `Fil de discussion` ouvre le flux interactif de la session.

## Traitement batch Spark

Le service optionnel `spark-batch` promeut `opencode.events_bronze` vers
`opencode.events`, puis ecrit les tables Iceberg `opencode.session_summary` et
`opencode.tool_summary`. Le dashboard conserve son acces interactif
DuckDB/Iceberg ; Spark est reserve aux traitements batch executes a la demande.

## Requetes Spark

L'onglet `Requetes Spark` execute des requetes SQL de lecture sur la vue
`events`, alimentee par un snapshot Iceberg de `opencode.events`. Les requetes
`SELECT`, `WITH`, `SHOW`, `DESCRIBE` et `EXPLAIN` sont acceptees et limitees a
500 lignes. Les noms `opencode.events`, `opencode.session_summary` et
`opencode.tool_summary` sont automatiquement traduits vers le catalogue Spark.
