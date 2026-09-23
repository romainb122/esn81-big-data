# Apache Spark

## Role

Spark est un moteur de calcul distribue. Il construit un plan d'execution,
Il est utilise ici pour les requetes SQL et les agregats batch sur les tables
Iceberg.

Le projet utilise deux applications Spark :

- `spark-query` reste actif et execute le SQL envoye depuis le dashboard.
- `spark-batch` demarre ponctuellement et construit les tables Gold.

## Configuration actuelle : local[2]

Les deux applications sont lancees avec :

```text
--master local[2]
```

Il n'y a donc pas de Spark Master ni de Spark Worker independants dans la
configuration actuelle. Un seul conteneur execute le driver Spark et un
executeur local, avec au plus deux coeurs CPU.

Le driver analyse le SQL, consulte le catalogue Iceberg, construit le plan et
coordonne les tasks. L'executeur local lit les fichiers Parquet necessaires dans
S3 et calcule les resultats. Cette topologie est adaptee a une demonstration
locale, pas a un cluster distribue.

Un futur cluster Standalone utiliserait un Master, par exemple
`spark://spark-master:7077`, et un ou plusieurs Workers. Le Master recevrait
les applications et repartirait les executors sur les Workers.

## Lancement

Le service SQL demarre avec le projet :

```bash
docker compose up -d
```

Le batch est lance manuellement :

```bash
docker compose --profile spark run --build --rm spark-batch
```

Les deux partagent l'image `esn81-big-data-spark:local` et le fichier
`spark/conf/spark-defaults.conf`. Cette configuration active le catalogue
Iceberg REST et le connecteur Hadoop S3A.

## Entrees et sorties

| Application | Recoit | Produit |
| --- | --- | --- |
| `spark-query` | SQL de lecture en HTTP | JSON limite a 500 lignes |
| `spark-batch` | snapshot `opencode.events` | snapshots Gold Iceberg |

Le service SQL accepte `SELECT`, `WITH`, `SHOW`, `DESCRIBE` et `EXPLAIN`. Il
refuse les ecritures. Les noms publics `opencode.events`,
`opencode.session_summary` et `opencode.tool_summary` sont traduits vers les
identifiants Spark internes.

## Observer Spark

Les logs montrent les snapshots Iceberg, plans, stages, tasks et commits :

```bash
docker compose logs -f spark-query
docker compose --profile spark run --build --rm spark-batch
```

Spark demarre aussi Spark UI sur le port interne `4040`. Cette interface montre
les jobs, stages, tasks, temps d'execution, memoire et plans SQL. Elle est
consultable depuis le conteneur :

```bash
docker compose exec spark-query curl http://localhost:4040
```

Le port 4040 n'est pas expose sur la machine hote. Pour une demonstration de
cours dans le navigateur, il pourra etre publie explicitement dans Compose.
