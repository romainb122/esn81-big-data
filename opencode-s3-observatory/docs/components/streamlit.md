# Streamlit

## Role

Le service `dashboard` execute Streamlit et fournit l'interface web du projet
sur `http://localhost:8501`. Il presente les donnees sans les modifier.

Les vues actuelles sont :

- `Vue globale` : couts, tokens, modeles et outils.
- `Fil de discussion` : messages et outils par pages, du plus recent au plus
  ancien.
- `Requetes Spark` : editeur SQL execute par le service Spark interne.

Le bouton `Visualiser le flux de cette discussion` ouvre la page Plotly de flux
pour la session selectionnee.

## Lancement

```bash
docker compose up -d dashboard
```

Le conteneur recoit les URL internes S3, Iceberg et Spark SQL par variables
via HTTP.

## Chargement des donnees

Le dashboard charge un index Iceberg leger, mis en cache 60 secondes. Les champs
lourds comme le texte et les sorties d'outils ne sont charges que pour les
messages visibles du fil. Chaque page contient 12 messages.

Cette separation limite les transferts S3 et evite de rendre toute une longue
discussion au premier affichage. La page Flux charge la session complete
uniquement parce que son graphe a besoin de toutes les etapes.

## Formats recus et envoyes

| Echange | Format |
| --- | --- |
| Iceberg vers Streamlit | Arrow Table |
| DuckDB vers interface | DataFrame Pandas |
| formulaire SQL vers Spark | requete SQL dans un corps HTTP JSON |
| Spark vers interface | resultat HTTP JSON |

Streamlit affiche ensuite ces objets avec tableaux, graphiques Altair et flux
Plotly.
