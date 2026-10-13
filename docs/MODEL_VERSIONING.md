# Model Versioning and Rollback

This document explains how every part of the sentiment system is versioned, how a new model version is released, and how to go back to an older version quickly if something goes wrong.

## 1. What is versioned, and where

| Layer | How it is versioned | Where it lives |
|---|---|---|
| **Code** (cleaning, API, tests, pipeline) | Git commits, each with a short ID (SHA) such as `220149e` | GitHub: `hirenpatel1404/sentiment140-mlops` |
| **Model** | One file per version, `models/sentiment_model_vN.joblib`, plus a metadata file `models/sentiment_model_vN.json` | Git repository (`models/` folder) and inside the Docker image |
| **Training data** | The SHA-256 fingerprint of the CSV file is stored in the model metadata. If the data changes, the fingerprint changes | `data_sha256` field in the metadata |
| **Docker image** | Three tags for every build: `latest`, the model version (`v1`), and model version + commit (`v1-220149e`) | Docker Hub: `hirenpatel9/sentiment140-api` |
| **Deployment** | Kubernetes keeps a numbered history of every rollout (10 revisions are kept) | `kubectl rollout history deployment/sentiment-api` |

The `v1-<commit>` tag never moves. It always points to the exact image built from that commit, which is why it is the safest tag to roll back to. `latest` and `v1` move every time a new image is pushed.

## 2. Model registry

| Version | Date | Algorithm | Training rows | Test accuracy | Test F1 | Neutral band | Status |
|---|---|---|---|---|---|---|---|
| **v1** | 2026-10-12 | TF-IDF (1-2 grams) + Logistic Regression, C = 1.0 | 1,208,408 | 0.8231 | 0.8236 | 0.30-0.70 | **In production** |

Each new version gets a new row. The full details (settings, data fingerprint, scikit-learn version) are in the matching `.json` file.

## 3. The metadata file (example: v1)

```json
{
  "model_version": "v1",
  "algorithm": "TF-IDF (1-2 grams) + LogisticRegression",
  "hyperparameters": {"C": 1.0, "min_df": 5, "max_features": 300000, "ngram_range": [1, 2]},
  "neutral_band": [0.3, 0.7],
  "training_rows": 1208408,
  "data_sha256": "08cba6317a49528fcd074f9043aafcd5ad6c6be45ede159c4e36cec33af24afe",
  "test_metrics": {"accuracy": 0.8231, "f1": 0.8236, "roc_auc": 0.9018},
  "python": "3.14.2",
  "scikit_learn": "1.8.0"
}
```

The API reads this file at start-up. It takes its neutral band from the file, and reports the version and test accuracy on `GET /health`. So I can always ask a running pod which model it is serving.

## 4. How a new model version is released

1. **Train:** in `notebooks/01_sentiment_model.ipynb`, set `MODEL_VERSION = "v2"` and run it. This creates `sentiment_model_v2.joblib` and `sentiment_model_v2.json`. The `v1` files stay untouched.
2. **Compare:** v2 is only promoted if its test F1 is at least as good as v1's (0.8236) and it passes the API tests. I add a row to the registry table above.
3. **Point the service at v2:** change `MODEL_VERSION=v1` to `v2` in the `Dockerfile`, and in `k8s/deployment.yaml` change the image tag to `v2` and set the `MODEL_VERSION` env value and the `change-cause` note.
4. **Commit and push:** GitHub Actions runs the 25 tests. If they pass, it builds the image, smoke-tests it, and pushes `latest`, `v2` and `v2-<commit>` to Docker Hub. If any test fails, nothing is pushed.
5. **Deploy:** run `kubectl apply -f k8s/deployment.yaml`. Kubernetes performs a rolling update: new pods start and must pass the `/health` readiness check before the old pods are stopped, so there is no downtime.
6. **Verify:** run `curl http://localhost:8000/health`. The answer must show `"model_version": "v2"`.

## 5. How to roll back

Choose the option that matches the situation, from fastest to most permanent.

### Option A: Undo the last rollout (fastest, a few seconds)
Use this when a new release misbehaves right after deployment.
```
kubectl rollout history deployment/sentiment-api      # list revisions with their change-cause
kubectl rollout undo deployment/sentiment-api         # go back one revision
kubectl rollout undo deployment/sentiment-api --to-revision=1   # or go to a specific revision
kubectl rollout status deployment/sentiment-api       # wait until the rollback is finished
```

### Option B: Pin an exact image
Use this to return to a known-good build, even an old one.
```
kubectl set image deployment/sentiment-api sentiment-api=hirenpatel9/sentiment140-api:v1-220149e
```
The same works with plain Docker:
```
docker run -d -p 5000:5000 hirenpatel9/sentiment140-api:v1-220149e
```

### Option C: Switch only the model, keep the same image
Use this when the image contains several model files. The API chooses the model through the `MODEL_VERSION` environment variable, so no rebuild is needed.
```
kubectl set env deployment/sentiment-api MODEL_VERSION=v1
```

### Option D: Make the rollback permanent in Git
After an emergency rollback with A, B or C, fix the source so the next CI/CD run doesn't redeploy the bad version.
```
git revert <commit-of-the-bad-release>
git push            # CI/CD tests, rebuilds and pushes the corrected image
```

## 6. Why this works
- Old model files are never overwritten. Each version has its own file name.
- Every Docker image has a fixed `vN-<commit>` tag, so any past build can be run again exactly.
- Kubernetes stores the last 10 rollouts, so one command is enough to go back.
- Tests and a smoke test run before every push to Docker Hub, so a broken build never reaches the registry.
- `/health` reports the model version, so I can confirm which version is live after every change.
