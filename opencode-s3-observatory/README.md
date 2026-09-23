# OpenCode S3 Observatory

Application locale pour sauvegarder des sessions OpenCode dans SeaweedFS/S3,
les convertir en Parquet et les explorer dans un dashboard Streamlit avec
DuckDB.

## Demarrage rapide

Depuis ce dossier :

```bash
docker compose up -d --build
```

Ouvrir ensuite :

- Dashboard : `http://localhost:8501`
- API S3 : `http://localhost:8333`
- Documentation : `http://localhost:8502`

Les identifiants S3 sont uniquement destines a la demonstration locale :
`admin` / `bigdata-local-secret`, bucket `bigdata`, region `us-east-1`.

## Arborescence

```text
app/                         Dashboard Streamlit
scripts/                     Exports OpenCode et outils d'administration
docs/                        Site Docsify et documentation Markdown
examples/                    Exemple de signature POST S3
samples/                     Fichiers de test S3
local-exports/               Archives telechargees localement, non versionnees
docker-compose.yml           SeaweedFS et dashboard
```

## Commandes courantes

```bash
# Voir les conteneurs et leurs journaux
docker compose ps
docker compose logs -f dashboard
docker compose logs -f documentation

# Exporter tout de suite les sessions OpenCode modifiees
./scripts/export-opencode-conversations.sh --force

# Installer ou reconfigurer l'export automatique toutes les cinq minutes
./scripts/install-opencode-export-timer.sh

# Reconstruire la table Iceberg apres des exports de test repetes
.venv/bin/python scripts/rebuild-opencode-iceberg.py
./scripts/export-opencode-conversations.sh --force

# Generer des syntheses batch Spark dans Iceberg
docker compose --profile spark run --build --rm spark-batch

# Arreter les conteneurs sans supprimer les donnees S3
docker compose down
```

## Documentation

- [Sauvegardes OpenCode et consultation des fichiers S3](docs/operations/opencode-s3.md)
- [Architecture de la chaine de donnees](docs/guide/architecture.md)
- [Gouvernance des donnees et garanties ACID](docs/guide/data-governance.md)
- [Index de la documentation](docs/README.md)
- Test S3 sous PowerShell : `./scripts/test-s3.ps1`

Les exports conservent les prompts, reponses, commandes et sorties visibles en
clair. Les parties de raisonnement ne sont pas stockees. Le S3 doit rester
local et prive, car un prompt ou une sortie de commande peut contenir un secret.

## Vues du dashboard

Le dashboard propose trois vues explicites :

- `Vue globale` : volumes, couts, tokens, modeles et outils utilises.
- `Fil de discussion` : prompts, reponses et operations d'une session dans
  l'ordre chronologique.
- `Requetes Spark` : requetes SQL de lecture executees par Spark sur les
  fichiers Parquet S3.

Le bouton du `Fil de discussion` ouvre le flux interactif de la session.

## Traitement batch Spark

Le service optionnel `spark-batch` lit la table transactionnelle
`opencode.events` et ecrit les tables Iceberg `opencode.session_summary` et
`opencode.tool_summary`. Elles regroupent les sessions, tokens, couts et appels
d'outils sans reprendre les prompts ni les sorties. Le dashboard conserve son
acces interactif DuckDB/Iceberg ; Spark est reserve aux traitements batch
executes a la demande.

## Requetes Spark

L'onglet `Requetes Spark` execute des requetes SQL de lecture sur la vue
`events`, alimentee par un snapshot Iceberg de `opencode.events`. Les requetes
`SELECT`, `WITH`, `SHOW`, `DESCRIBE` et `EXPLAIN` sont acceptees et limitees a
500 lignes. Les noms `opencode.events`, `opencode.session_summary` et
`opencode.tool_summary` sont automatiquement traduits vers le catalogue Spark.
