# Flux de donnees

## 1. Capture et export

Le timer systemd lance `scripts/export-opencode-conversations.sh` toutes les
cinq minutes. Le script identifie les sessions OpenCode modifiees et execute
`opencode export` pour chacune.

`scripts/opencode-export-to-parquet.py` retire les parties `reasoning`, puis
produit un JSON visible et un Parquet d'evenements. Les fichiers sont envoyes
dans le bucket S3 `bigdata`.

```text
OpenCode export JSON
  -> nettoyage des parties reasoning
  -> JSON visible + Parquet d'evenements
  -> SeaweedFS/S3, couche Bronze
```

## 2. Publication transactionnelle

Apres l'upload Bronze, `scripts/sync-opencode-iceberg.py` lit le Parquet et
committe la session dans `opencode.events`. Le commit Iceberg publie un nouveau
snapshot atomiquement. Si cette etape echoue, les lecteurs restent sur le
snapshot precedent.

```text
Parquet Bronze
  -> PyArrow Table
  -> PyIceberg overwrite de la session
  -> snapshot opencode.events, couche Silver
```

## 3. Consultation interactive

Streamlit charge depuis Iceberg un index leger sans texte ni sorties d'outils.
DuckDB le transforme en vue temporaire pour produire les metriques et listes de
sessions. Lorsqu'un fil est consulte, seules les pages visibles de messages sont
chargees completement.

```text
Iceberg snapshot
  -> Arrow Table en memoire
  -> vue DuckDB temporaire
  -> DataFrame et composants Streamlit
```

## 4. Requetes et batch Spark

Le dashboard envoie le SQL a `spark-query`. Ce service lit le snapshot Iceberg,
execute la requete et renvoie au dashboard un resultat JSON limite a 500 lignes.

Le job `spark-batch` lit lui aussi `opencode.events`. Il agrege les sessions et
outils, puis publie des snapshots dans les tables Gold.

```text
opencode.events
  -> Spark SQL : resultat JSON vers le dashboard
  -> Spark batch : opencode.session_summary et opencode.tool_summary
```

## Fraicheur des donnees

`opencode.events` est a jour apres le prochain export de session. Les tables
Gold sont a jour apres le prochain lancement de `spark-batch`. Elles peuvent
donc etre temporairement en retard par rapport a la table Silver.
