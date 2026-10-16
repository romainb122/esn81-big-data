# Flux de donnees

## 1. Capture et export

L'extension pi ecoute `message_end`. A chaque message finalise, elle retire les
blocs `thinking` et publie immediatement les evenements visibles dans Redpanda.
Les scripts `pi-export-to-events.py` et `publish-events.py` sont reserves au
rejeu ou a l'import manuel.

```text
Hook pi `message_end`
  -> nettoyage des blocs thinking
  -> POST REST /topics/opencode.events
  -> topic Redpanda
```

## 2. Branche temps réel Arroyo

En parallèle de l'ingestion Iceberg, Arroyo consomme `opencode.events` avec son
connecteur Kafka. Le pipeline SQL `conversation-observatory-live` conserve les
événements texte dont le rôle est `assistant`, puis écrit le résultat dans son
`PreviewSink`.

Le dashboard HTML ouvre une connexion `EventSource` directement sur la sortie
SSE du job Arroyo. Chaque événement modifie uniquement le DOM et les compteurs
locaux : il n'y a ni polling ni rechargement de page.

```text
opencode.events
  -> Arroyo KafkaSource
  -> filtre SQL assistant/text
  -> PreviewSink
  -> SSE
  -> dashboard HTML :8503
```

Cette branche est instantanée mais éphémère. L'historique et les analyses
restent sous la responsabilité d'Iceberg.

## 3. Ingestion Bronze

`iceberg-sink` consomme le topic avec le groupe
`opencode-iceberg-bronze`. Il ajoute chaque lot dans
`opencode.events_bronze`, puis committe son offset Redpanda seulement apres le
commit du snapshot Iceberg. Une interruption avant ce commit peut rejouer un
lot : Bronze est donc un journal append-only.

```text
Topic Redpanda
  -> PyArrow Table
  -> PyIceberg append
  -> snapshot opencode.events_bronze, couche Bronze
```

## 4. Promotion Silver

Le premier etage de `spark-batch` prend, pour chaque session, les evenements du
plus recent `exported_at_ms`, deduplique `event_id`, puis publie un nouveau
snapshot de `opencode.events`. Les consommateurs voient donc soit la version
Silver precedente, soit la version complete apres promotion.

## 5. Consultation interactive historique

Streamlit charge directement depuis la table Iceberg Bronze un index léger afin
d'afficher les nouveaux événements sans attendre un batch Spark. DuckDB
élimine localement les doublons et garde la dernière version de chaque événement.
DuckDB le transforme en vue temporaire pour produire les metriques et listes de
sessions. Lorsqu'un fil est consulte, seules les pages visibles de messages sont
chargees completement.

```text
Iceberg snapshot
  -> Arrow Table en memoire
  -> vue DuckDB temporaire
  -> DataFrame et composants Streamlit
```

## 6. Requetes et batch Spark

Le dashboard envoie le SQL a `spark-query`. Ce service lit le snapshot Iceberg,
execute la requete et renvoie au dashboard un resultat JSON limite a 500 lignes.

Le second etage de `spark-batch` lit `opencode.events`. Il agrege les sessions
et outils, puis publie des snapshots dans les tables Gold.

```text
opencode.events
  -> Spark SQL : resultat JSON vers le dashboard
  -> Spark batch : opencode.session_summary et opencode.tool_summary
```

## Fraicheur des donnees

Le dashboard HTML reçoit un événement dès sa sortie du pipeline Arroyo, sans
attendre Iceberg. Bronze est à jour après le commit du consommateur Redpanda.
Silver et Gold sont à jour après le prochain lancement de `spark-batch`; elles
peuvent donc être temporairement en retard par rapport à Bronze.
