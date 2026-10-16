# Arroyo et dashboard temps réel

## Objectif

Ce chemin affiche les réponses finalisées sans polling, sans rechargement de page et sans attendre Iceberg :

```text
Pi / OpenCode
    → Redpanda (`opencode.events`)
    → Arroyo (`conversation-observatory-live`)
    → PreviewSink SSE
    → navigateur HTML
```

Il fonctionne en parallèle du chemin analytique historique :

```text
Redpanda → Iceberg Bronze → DuckDB / Spark → Streamlit
```

## Services et ports

| Service | Fonction | URL locale |
| --- | --- | --- |
| `live-dashboard` | Dashboard HTML sans état serveur | `http://localhost:8503` |
| `arroyo` | Moteur de streaming, API et interface d'administration | `http://localhost:8510` |
| `dashboard` | Dashboard Streamlit historique | `http://localhost:8501` |
| `iceberg-sink` | Ingestion Bronze et ancien canal de notification | SSE sur `http://localhost:8504/events` |

Les ports sont liés à `127.0.0.1` et ne sont donc pas exposés sur le réseau local.

## Déroulement d'un événement

1. Le hook Pi `message_end`, ou le plugin OpenCode à la fin d'une session active, produit un événement JSON.
2. L'événement est publié dans le topic Redpanda `opencode.events`.
3. Arroyo consomme directement ce topic avec son connecteur Kafka.
4. La requête SQL conserve seulement les événements visibles répondant à :

   ```sql
   role = 'assistant' AND event_type = 'text'
   ```

5. Le résultat arrive dans le `PreviewSink` Arroyo.
6. Le navigateur maintient une connexion `EventSource` sur la sortie du job :

   ```text
   /api/v1/pipelines/{pipeline_id}/jobs/{job_id}/output
   ```

7. À chaque message SSE, JavaScript ajoute la réponse en haut du flux et actualise les compteurs dans le DOM. La page n'est jamais rechargée.

Le navigateur découvre automatiquement l'identifiant du pipeline et celui du job actif via l'API Arroyo. Ces identifiants ne sont donc pas codés en dur dans le HTML.

## Pipeline SQL

La requête est versionnée dans :

```text
config/arroyo-live.sql
```

Le pipeline porte le nom :

```text
conversation-observatory-live
```

Il utilise :

```sql
connector = 'kafka'
bootstrap_servers = 'redpanda:9092'
topic = 'opencode.events'
format = 'json'
'source.offset' = 'latest'
```

`latest` signifie que le dashboard direct montre les événements reçus après le démarrage du pipeline. L'historique durable reste disponible dans Iceberg et Streamlit.

## Provisionnement automatique

Le service éphémère `arroyo-init` exécute :

```text
scripts/provision-arroyo.py
```

Au démarrage, il :

1. attend l'API Arroyo ;
2. cherche un pipeline nommé `conversation-observatory-live` ;
3. valide la requête SQL ;
4. crée le pipeline seulement s'il n'existe pas déjà.

Le script est idempotent. La base de configuration Arroyo est conservée dans le volume Docker `esn81-big-data_arroyo-data`.

## Métriques affichées

Pour chaque réponse, le dashboard distingue :

- **Tokens entrée** : nouveaux tokens d'entrée facturés ;
- **Tokens sortie** : réponse générée ;
- **Cache lu** : contexte relu depuis le cache du fournisseur ;
- **Raisonnement** : tokens de raisonnement lorsqu'ils sont exposés ;
- **Volume traité** : entrée + sortie + cache lu/écrit + raisonnement ;
- **Coût observé** : coût transmis par le fournisseur, sans estimation locale.

Exemple :

```text
Entrée          445
Sortie            5
Cache lu     140 288
Raisonnement       0
Volume traité 140 738
```

Les champs absents restent à zéro dans cette vue instantanée. Aucune métrique n'est inventée.

Les compteurs du haut sont cumulatifs uniquement depuis l'ouverture de la page. Le bouton **Effacer l'écran** vide la vue locale du navigateur ; il ne supprime rien dans Redpanda ou Iceberg.

## Résilience

- `EventSource` se reconnecte automatiquement si le flux SSE est interrompu.
- Si Arroyo redémarre, le dashboard recherche de nouveau le pipeline et le job actif.
- Arroyo réalise des checkpoints réguliers de son pipeline.
- Le stockage analytique Redpanda → Iceberg continue indépendamment du dashboard direct.

## Exploitation

```bash
# État des services
docker compose ps arroyo arroyo-init live-dashboard

# Logs du moteur et du pipeline
docker compose logs -f arroyo

# Vérifier les jobs du pipeline depuis l'interface
xdg-open http://localhost:8510

# Relancer les composants temps réel
docker compose up -d arroyo-init live-dashboard
```

Si le dashboard reste sur « Recherche du pipeline Arroyo », vérifier que le job est dans l'état `Running` dans l'interface Arroyo.
