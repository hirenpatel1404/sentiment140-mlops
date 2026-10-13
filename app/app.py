"""
Flask API for the Sentiment140 model.

Endpoints
  GET  /              short description of the API
  GET  /health        is the service up, and which model version is loaded?
  POST /predict       {"text": "..."}            -> sentiment of one tweet
  POST /predict/batch {"texts": ["...", "..."]}  -> sentiment of up to 100 tweets
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

import joblib
from flask import Flask, jsonify, request

# I make the shared src/ folder importable, so the API cleans text exactly like the notebook
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.preprocess import preprocess  # noqa: E402

MODEL_DIR = Path(os.getenv("MODEL_DIR", ROOT / "models"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1")      # I switch or roll back versions with this variable
MAX_CHARS = 1000
MAX_BATCH = 100

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentiment-api")


def load_model(version: str):
    # I load the model file and its metadata (neutral band, metrics) for the requested version
    model = joblib.load(MODEL_DIR / f"sentiment_model_{version}.joblib")
    with open(MODEL_DIR / f"sentiment_model_{version}.json") as f:
        meta = json.load(f)
    return model, meta


model, meta = load_model(MODEL_VERSION)
NEUTRAL_LOW, NEUTRAL_HIGH = meta["neutral_band"]
log.info("Loaded model %s (neutral band %.2f-%.2f)", MODEL_VERSION, NEUTRAL_LOW, NEUTRAL_HIGH)

app = Flask(__name__)


def classify(texts):
    # I clean each tweet, get the probability of positive, then map it to positive / neutral / negative
    clean = [preprocess(t) for t in texts]
    probs = model.predict_proba(clean)[:, 1]
    results = []
    for raw, c, p in zip(texts, clean, probs):
        p = float(p)
        if p > NEUTRAL_HIGH:
            label, confidence = "positive", p
        elif p < NEUTRAL_LOW:
            label, confidence = "negative", 1 - p
        else:
            label, confidence = "neutral", 1 - abs(p - 0.5) * 2   # closest to 0.5 = most neutral
        results.append({"text": raw, "clean_text": c, "sentiment": label,
                        "confidence": round(confidence, 4), "prob_positive": round(p, 4)})
    return results


def validate_text(t):
    # I return an error message, or None when the text is fine
    if not isinstance(t, str):
        return "'text' must be a string"
    if not t.strip():
        return "'text' must not be empty"
    if len(t) > MAX_CHARS:
        return f"'text' must be at most {MAX_CHARS} characters"
    return None


@app.get("/")
def index():
    return jsonify({"service": "Sentiment140 sentiment API", "model_version": MODEL_VERSION,
                    "endpoints": {"GET /health": "status", "POST /predict": {"text": "your tweet"},
                                  "POST /predict/batch": {"texts": ["tweet 1", "tweet 2"]}}})


@app.get("/health")
def health():
    return jsonify({"status": "ok", "model_version": MODEL_VERSION,
                    "test_accuracy": meta.get("test_metrics", {}).get("accuracy")})


@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "text" not in data:
        return jsonify({"error": "Send JSON like {\"text\": \"I love this!\"}"}), 400
    err = validate_text(data["text"])
    if err:
        return jsonify({"error": err}), 400
    t0 = time.perf_counter()
    result = classify([data["text"]])[0]
    result["model_version"] = MODEL_VERSION
    result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    log.info("predict sentiment=%s p=%.3f", result["sentiment"], result["prob_positive"])
    return jsonify(result), 200


@app.post("/predict/batch")
def predict_batch():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("texts"), list) or not data["texts"]:
        return jsonify({"error": "Send JSON like {\"texts\": [\"tweet 1\", \"tweet 2\"]}"}), 400
    if len(data["texts"]) > MAX_BATCH:
        return jsonify({"error": f"At most {MAX_BATCH} texts per request"}), 400
    for i, t in enumerate(data["texts"]):
        err = validate_text(t)
        if err:
            return jsonify({"error": f"item {i}: {err}"}), 400
    results = classify(data["texts"])
    return jsonify({"model_version": MODEL_VERSION, "count": len(results), "results": results}), 200


if __name__ == "__main__":
    # I use Flask's built-in server only for local testing; Docker uses gunicorn
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
