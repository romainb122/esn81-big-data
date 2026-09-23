# Architecture de la chaine de donnees

## Vue d'ensemble

```text
OpenCode
  -> script d'export automatique
  -> JSON visible et Parquet d'evenements
  -> SeaweedFS, bucket S3 bigdata
  -> table Iceberg opencode.events
  -> dashboard Streamlit et analyses DuckDB

Table Iceberg opencode.events
  -> Spark batch
  -> tables Iceberg de synthese

Dashboard
  -> service Spark SQL interne
  -> requetes Spark sur un snapshot Iceberg
```

Le projet separe le stockage durable, la consultation interactive et les
traitements analytiques plus lourds. Cette separation evite de demarrer Spark
pour chaque clic dans le dashboard.

Les fichiers S3 bruts constituent une zone d'atterrissage. Les tables Iceberg
constituent la frontiere transactionnelle et la source de verite analytique.
Les garanties et limites ACID sont detaillees dans
[Gouvernance et garanties ACID](data-governance.md).

## Source : OpenCode

OpenCode est la source des donnees. Une session peut contenir des prompts,
reponses visibles, appels d'outils, commandes, sorties de commandes,
delegations a des sous-agents, couts et consommation de tokens.

Les parties de raisonnement interne ne sont volontairement ni exportees, ni
stockees, ni affichees. Les prompts et sorties d'outils restent en clair : le
stockage S3 doit donc rester local et prive.

## Export et formats de donnees

Le script `scripts/export-opencode-conversations.sh` est le point d'entree de
l'export. Le timer utilisateur `opencode-s3-export.timer` le lance au demarrage
puis toutes les cinq minutes. Seules les sessions dont la date de mise a jour a
change sont exportees.

Pour chaque session, le script execute les etapes suivantes :

1. Il appelle `opencode export` pour obtenir la session source.
2. `scripts/opencode-export-to-parquet.py` retire les parties de raisonnement.
3. Le script produit un JSON visible et un fichier Parquet avec une ligne par
   evenement.
4. Les deux fichiers sont envoyes vers SeaweedFS au moyen de son API S3.
5. `scripts/sync-opencode-iceberg.py` synchronise les evenements dans Iceberg.

Le JSON est une archive lisible d'une discussion. Le Parquet est un format
colonnaire : il est plus adapte aux filtres, agregats et scans analytiques de
DuckDB et Spark.

## Stockage S3 : SeaweedFS

Le service Docker `s3` utilise SeaweedFS et expose une API compatible S3 sur
`http://localhost:8333`. Il remplace AWS S3 pour cet environnement local.

Le bucket utilise est `bigdata`. Les chemins importants sont :

- `opencode-observatory/sessions/ses_xxx.json` : archive JSON visible.
- `opencode-observatory/parquet/sessions/ses_xxx.parquet` : evenements bruts
  en Parquet.
- `iceberg/opencode/events/` : fichiers de donnees et metadonnees de la table
  Iceberg.
- `iceberg/opencode/session_summary/` : donnees et metadonnees de la synthese
  de sessions.
- `iceberg/opencode/tool_summary/` : donnees et metadonnees de la synthese des
  appels d'outils.

Le volume Docker `esn81-big-data_s3-data` est nomme explicitement. Les donnees
restent donc disponibles si le projet est deplace ou si les conteneurs sont
arretes sans suppression des volumes.

## Table analytique : Apache Iceberg

Le service `iceberg` execute le catalogue REST Apache Iceberg sur
`http://localhost:8181`. Iceberg ne remplace pas S3 : il ajoute une table,
des metadonnees et des versions au-dessus de fichiers Parquet stockes dans S3.

La table active est `opencode.events`. Elle permet au dashboard de lire une vue
coherente des evenements. Lorsqu'une session est reexportee,
`sync-opencode-iceberg.py` remplace la copie active de cette session pour eviter
les doublons. Les snapshots precedents restent geres par Iceberg.

La bibliotheque Python PyIceberg est utilisee par les scripts d'export et par le
dashboard pour acceder au catalogue REST, a la table et au stockage S3.

## Dashboard : Streamlit et DuckDB

Le service `dashboard` execute Streamlit sur `http://localhost:8501`. Il est
l'interface de consultation des sessions et des analyses courantes.

Streamlit construit l'interface web, les filtres, les tableaux et les pages du
dashboard. Altair est utilise pour certains graphiques et Plotly pour le flux
interactif de discussion.

DuckDB est le moteur SQL local embarque dans le dashboard. Il est adapte aux
analyses interactives courtes : regroupements par modele, outils utilises,
metriques de cout et tokens, ou recherche dans une session.

Pour eviter de charger les contenus lourds au premier affichage, le dashboard
lit d'abord un index Iceberg leger, sans prompts ni sorties d'outils. Dans la
vue `Fil de discussion`, il charge ensuite 12 messages complets a la fois, du
plus recent au plus ancien. Le bouton de chargement ajoute la page suivante de
messages plus anciens. Le bouton `Visualiser le flux de cette discussion`
charge la session complete dans la page Flux, car son graphe a besoin de toutes
les etapes.

## Spark batch

Le service optionnel `spark-batch` est un job Apache Spark lance a la demande :

```bash
docker compose --profile spark run --build --rm spark-batch
```

Spark lit un snapshot de `opencode.events` via le catalogue Iceberg REST. Il
remplace atomiquement les tables Iceberg d'agregats, sans contenu de
conversation ni sortie de commande :

- `opencode.session_summary` : une ligne par session avec compteurs, tokens et
  couts.
- `opencode.tool_summary` : nombre d'appels par session, outil et statut.

Spark est reserve a ces traitements batch, qui peuvent lire un volume de donnees
plus important sans ralentir la navigation du dashboard.

## Requetes Spark SQL

Le service `spark-query` est un processus Spark interne demarre avec le
dashboard. Il expose un endpoint HTTP uniquement sur le reseau Docker, sans
port publie sur la machine hote. L'onglet `Requetes Spark` du dashboard lui
envoie les requetes SQL.

La vue Spark `events` lit la table transactionnelle `opencode.events`. Les noms
`opencode.events`, `opencode.session_summary` et `opencode.tool_summary` sont
automatiquement traduits vers les identifiants du catalogue Spark, ce qui permet
de reutiliser les requetes du dashboard tout en conservant un snapshot coherent.

Par securite, le service accepte seulement `SELECT`, `WITH`, `SHOW`,
`DESCRIBE` et `EXPLAIN`. Il refuse les ecritures et limite chaque resultat a
500 lignes. Spark SQL accepte la majorite du SQL ANSI courant ; les requetes
specifiques a PostgreSQL ou DuckDB peuvent necessiter une adaptation.

## Roles des briques

- OpenCode : produit les sessions et les traces visibles.
- scripts Python et Bash : extraient, nettoient, convertissent et synchronisent
  les donnees.
- PyArrow : ecrit les fichiers Parquet pendant l'export.
- SeaweedFS : stocke localement les objets compatibles S3.
- Apache Iceberg : versionne et organise la table analytique active.
- PyIceberg : permet aux applications Python de manipuler Iceberg.
- Streamlit : fournit le dashboard web.
- DuckDB : execute les analyses SQL interactives dans le dashboard.
- Apache Spark : execute les agregats batch et les requetes SQL lourdes sur S3.
- Docker Compose : demarre et relie les services du projet.
- systemd --user : planifie l'export automatique des sessions OpenCode.

## Pourquoi DuckDB et Spark sont tous les deux presents

DuckDB est privilegie pour les interactions rapides du dashboard : il demarre
vite et traite efficacement les donnees deja chargees pour une consultation.
Spark est utilise lorsque la requete ou le traitement doit travailler directement
sur les fichiers Parquet S3, ou lorsque le volume de donnees devient trop grand
pour un traitement interactif simple. Iceberg assure entre les deux une table
versionnee et coherente pour les donnees actives.
