# Intégration pi en temps réel

L'extension `pi/extensions/observatory-export.ts` écoute le hook `message_end`.
Chaque message finalisé est envoyé immédiatement à Redpanda. Les blocs
`thinking` et les messages système sont exclus.

## Installation recommandée

Installe l'extension au niveau utilisateur afin qu'elle soit disponible dans
toutes les sessions pi :

```bash
cd /home/romain/bigdata/esn81-big-data/opencode-s3-observatory
chmod +x scripts/install-pi-extension.sh
./scripts/install-pi-extension.sh
```

Le script crée ce lien :

```text
~/.pi/agent/extensions/conversation-observatory.ts
```

L'extension utilise par défaut :

```text
Redpanda REST : http://localhost:18082
topic         : opencode.events
```

Ces valeurs peuvent être changées avec `REDPANDA_PROXY_URL` et
`REDPANDA_TOPIC`.

## Activer une session

Après l'installation :

- redémarrer Pi ; ou
- exécuter `/reload` dans une session déjà ouverte.

Pour vérifier que l'extension est active, envoyer un message puis surveiller :

```bash
cd /home/romain/bigdata/esn81-big-data/opencode-s3-observatory
docker compose logs -f iceberg-sink
```

Un nouvel ajout Bronze doit apparaître immédiatement. Le dashboard lit Bronze
pour afficher les événements récents, sans attendre le batch Spark.

## Vérifier les données analytiques

Silver et Gold sont mises à jour à la demande :

```bash
docker compose --profile spark run --rm spark-batch
```

Le script `pi-export-to-events.py` reste disponible uniquement pour rejouer une
session historique ou récupérer des événements après une interruption.
