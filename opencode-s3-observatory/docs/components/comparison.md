# Comparateur technique

Le comparateur stocke les exécutions d'un même prompt sur plusieurs modèles ou
harnais. La première version mesure uniquement les données techniques
réellement disponibles :

- tokens d'entrée, de sortie et total ;
- coût ;
- durée ;
- température ;
- taille du contexte et contexte utilisé.

Aucune valeur n'est inventée. Une métrique absente est laissée vide.
L'évaluation de la qualité et JEV seront ajoutés dans une étape ultérieure.

## Table Iceberg

```text
opencode.comparison_runs
```

## Exécution normalisée

Le runner accepte des adaptateurs de commandes explicites. Exemple de configuration :

```json
{"adapters":[
  {"harness":"Pi","provider":"openai-codex","model":"gpt-5","command":["pi","--print"]},
  {"harness":"Codex","provider":"openai-codex","model":"gpt-5","command":["codex","exec","-"]}
]}
```

Chaque commande reçoit exactement le même prompt sur son entrée standard. Le
runner mesure toujours la durée ; les autres métriques sont prises uniquement
si la commande les fournit en JSON.

```bash
python scripts/run-comparison.py "Explique X" --config adapters.json --output runs.jsonl
```

## Import JSONL

Une ligne représente une exécution :

```json
{"comparison_id":"test-001","prompt":"Explique X","harness":"Pi","provider":"openai-codex","model":"gpt-5","input_tokens":120,"output_tokens":80,"total_tokens":200,"cost":0.002,"duration_ms":4200}
```

Un lancement complet utilisant les adaptateurs configurés se fait avec une seule
commande :

```bash
./scripts/run-technical-comparison.sh "Explique le fonctionnement de Kafka"
```

Le script lance le même prompt sur Pi, Codex et OpenCode, mesure les résultats
disponibles, puis les écrit dans Iceberg. Les commandes sont définies dans
`config/comparison-adapters.json` et peuvent être adaptées aux modèles
accessibles.

Pour importer séparément un fichier JSONL :

```bash
python scripts/record-comparison.py runs.jsonl
```

Les champs inconnus sont ignorés. Le dashboard est accessible depuis le bouton
`Comparateur technique` dans la barre latérale.
