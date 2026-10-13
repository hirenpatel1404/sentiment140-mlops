# Sentiment140 MLOps – End-to-End Twitter Sentiment Analysis

An end-to-end machine learning system that classifies tweets as **positive**, **negative** or **neutral**. It covers data cleaning, a logistic regression model, a Flask API, Docker, CI/CD with GitHub Actions, model versioning and rollback, and autoscaling deployment on Kubernetes.

**Student:** Hiren Patel, DAAI (Data Analytics and Artificial Intelligence), Willis College
**Docker image:** [`hirenpatel9/sentiment140-api`](https://hub.docker.com/r/hirenpatel9/sentiment140-api)
**Full report:** `docs/Final_Project_Report_Sentiment140_MLOps.pdf`

## Results
| Metric (test set, 151,052 tweets) | Value |
|---|---|
| Accuracy | 0.8231 |
| F1-score | 0.8236 |
| ROC AUC | 0.9018 |
| Neutral band (probability positive) | 0.30-0.70, which labels about 27% of tweets neutral |
| Accuracy on the remaining positive/negative answers | 0.8966 |
| Model size / prediction time | 5.9 MB / about 0.2 ms per tweet |
| Automated tests | 25 passing |
| Kubernetes autoscaling | 2 to 6 pods under load, then back to 2 |

## Project structure
```
notebooks/01_sentiment_model.ipynb   data inspection, cleaning, training, evaluation (with interpretations)
src/preprocess.py                    shared tweet cleaning (used by notebook AND API)
models/sentiment_model_v1.joblib     trained model (TF-IDF + logistic regression) + .json metadata
app/app.py                           Flask API: /health, /predict, /predict/batch
tests/                               25 pytest tests (cleaning + API)
Dockerfile, .dockerignore            container (python:3.12-slim + gunicorn)
.github/workflows/ci-cd.yml          CI: tests -> CD: build, smoke-test, push to Docker Hub
k8s/                                 Deployment, Service, HorizontalPodAutoscaler, load test
docs/MODEL_VERSIONING.md             versioning and rollback guide
docs/CHALLENGES.md                   problems I hit and how I solved them
docs/screenshots/                    evidence: tests, Docker, Docker Hub, Actions, autoscaling
reports/                             charts from the notebook
```

## Run it
```bash
# 1. Tests and local API
python -m pip install -r requirements-dev.txt
python -m pytest -v
python app/app.py                                      # http://localhost:5000

# 2. Docker (published image)
docker run -d -p 5000:5000 hirenpatel9/sentiment140-api:v1

# 3. Kubernetes (Docker Desktop)
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml -f k8s/hpa.yaml   # http://localhost:8000

# Try it
curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{"text": "I love this phone!"}'
```

## Data
Sentiment140, 1.6 million tweets labelled 0 (negative) or 4 (positive). The file is too large for GitHub, so it is not in this repository. To retrain, download `training.1600000.processed.noemoticon.csv` (for example from Kaggle, "kazanova/sentiment140") into `data/`.
