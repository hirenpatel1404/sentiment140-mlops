"""API tests: the service must accept requests and return the correct sentiment."""
import pytest
from app.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["model_version"]


@pytest.mark.parametrize("text", ["I love this phone, the camera is amazing!",
                                  "Best day ever, thank you so much :)",
                                  "I can't wait for the weekend!!!"])
def test_positive_tweets(client, text):
    r = client.post("/predict", json={"text": text})
    assert r.status_code == 200
    assert r.get_json()["sentiment"] == "positive"


@pytest.mark.parametrize("text", ["Worst customer service ever. Never buying again.",
                                  "I hate Mondays, so sad and tired",
                                  "my phone broke again, this sucks"])
def test_negative_tweets(client, text):
    r = client.post("/predict", json={"text": text})
    assert r.status_code == 200
    assert r.get_json()["sentiment"] == "negative"


@pytest.mark.parametrize("text", ["The meeting is on Tuesday.", "The report is attached"])
def test_neutral_tweets(client, text):
    r = client.post("/predict", json={"text": text})
    assert r.status_code == 200
    assert r.get_json()["sentiment"] == "neutral"


def test_response_format(client):
    body = client.post("/predict", json={"text": "@john I love it! http://t.co/x"}).get_json()
    for key in ["text", "clean_text", "sentiment", "confidence", "prob_positive", "model_version", "latency_ms"]:
        assert key in body
    assert body["clean_text"] == "i love it"
    assert 0.0 <= body["confidence"] <= 1.0


@pytest.mark.parametrize("payload", [None, {}, {"txt": "hi"}, {"text": ""}, {"text": "   "},
                                     {"text": 123}, {"text": "a" * 1001}])
def test_bad_requests_return_400(client, payload):
    r = client.post("/predict", json=payload) if payload is not None else client.post("/predict", data="not json")
    assert r.status_code == 400
    assert "error" in r.get_json()


def test_batch(client):
    r = client.post("/predict/batch", json={"texts": ["I love it", "I hate it"]})
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 2
    assert [x["sentiment"] for x in body["results"]] == ["positive", "negative"]


def test_batch_limits(client):
    assert client.post("/predict/batch", json={"texts": []}).status_code == 400
    assert client.post("/predict/batch", json={"texts": ["ok"] * 101}).status_code == 400
