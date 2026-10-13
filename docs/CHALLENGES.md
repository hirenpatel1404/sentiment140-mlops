# Challenges and How I Solved Them

This file records every problem I hit during the project and what I did about it, in simple language.

## 1. The wrong dataset was attached to the course page
**Problem:** The file I first downloaded (`train.csv`, 524 MB) had columns called `pixel_0, pixel_1, ...`. That is image data (CIFAR-10 from Assignment 6), not tweets.
**Fix:** I downloaded the real Sentiment140 file (`training.1600000.processed.noemoticon.csv`, 1.6 million tweets) from Kaggle. I checked that it has 6 columns (label, id, date, query, user, text) and that the labels are 0 and 4.

## 2. The data file is too big for GitHub
**Problem:** The CSV is 230 MB, and GitHub blocks files over 100 MB.
**Fix:** I added `data/` to `.gitignore`, so the data stays on my laptop only. The README explains where to download it. Only the small trained model (about 6 MB) goes into the repository.

## 3. The text encoding is not UTF-8
**Problem:** Some tweets contain special characters, and pandas fails or shows garbage if it reads the file as UTF-8.
**Fix:** I read the file with `encoding="latin-1"`, which is the encoding the dataset was saved in.

## 4. Splitting crashed with pandas 3
**Problem:** With pandas 3, text columns are stored in a new format (Arrow strings). scikit-learn's `train_test_split` crashed with the error "only integer scalar arrays can be converted to a scalar index".
**Fix:** I convert the text column to a normal NumPy array first with `.to_numpy(dtype=object)`.

## 5. Same cleaning in training and in the API (training/serving skew)
**Problem:** If the notebook cleans text one way and the Flask API cleans it slightly differently, the model receives different input in production and quietly makes worse predictions.
**Fix:** I put the cleaning code in one shared file, `src/preprocess.py`. Both the notebook and the API import it, so the cleaning is always identical.

## 6. Cleaning broke negative words
**Problem:** Removing all special characters turned "can't" into "can t". The important negative meaning was lost, and "t" is a useless token.
**Fix:** I remove apostrophes first ("can't" becomes "cant"), so negations survive as single words. I also shorten stretched words ("sooooo" becomes "soo"), so they match each other.

## 7. Duplicate and contradictory tweets
**Problem:** About 16,000 tweets appear more than once, and about 2,200 texts appear with BOTH a positive and a negative label. That is confusing for the model and also makes the test score too optimistic, because the same tweet can end up in both train and test.
**Fix:** After cleaning, I removed empty tweets, duplicates, and texts with conflicting labels (about 89,000 rows in total).

## 8. The dataset has no neutral tweets, but the project needs a neutral class
**Problem:** Sentiment140 only has positive (4) and negative (0) labels. In my first version, I called a tweet neutral when the model's probability was between 0.40 and 0.60. But plain factual sentences like "The meeting is on Tuesday" still came out as **positive** (probability 0.67).
**Why:** A tweet with no emotion words gets a probability of about 0.67 from the model's intercept (its starting point), not 0.50. So the 0.40-0.60 band was in the wrong place.
**Fix:** I now measure the probability the model gives to an empty tweet, and choose the smallest band around 0.5 that contains it (0.30-0.70). Tweets with no clear emotion now come out neutral. The trade-off is that more tweets are called neutral (about 27%), but the positive and negative answers that remain are more accurate (about 90%).
**Limitation:** This is an approximation. A truly reliable neutral class would need training data that is labelled neutral, or a model like BERT.

## 9. The trained model file was huge
**Problem:** scikit-learn's TF-IDF vectorizer keeps a list of every rare word it removed (`stop_words_`). With 1.6 million tweets, this list makes the saved model very large.
**Fix:** I delete that attribute before saving, because prediction doesn't need it. With compression, the model is about 6 MB.

## 10. Training on 1.6 million tweets takes time
**Problem:** Trying different settings on the full data is slow.
**Fix:** I build the TF-IDF features once and reuse them for all 4 values of C. I use the fast `liblinear` solver. On my laptop the full notebook runs in a few minutes.

## 11. Windows line endings (LF vs CRLF warnings)
**Problem:** When I ran `git add`, Git showed warnings like "LF will be replaced by CRLF". Windows ends lines differently (CRLF) from Linux (LF). Docker containers and GitHub Actions run on Linux, and scripts with Windows line endings can fail there.
**Fix:** I added a `.gitattributes` file that tells Git to always store text files with Linux line endings (LF).

## 12. gunicorn does not run on Windows
**Problem:** In production the API should run on gunicorn (a proper web server), not Flask's built-in test server. But gunicorn only works on Linux and macOS.
**Fix:** On my Windows laptop I test the API with `python app/app.py` (the Flask server) and with `pytest`. Inside the Docker container, which is Linux, the API runs on gunicorn.

## 13. "!!" inside a curl command changed my tweet
**Problem:** When I tested the API with curl in Git Bash, the tweet "I absolutely love this new phone!!" arrived at the API as "...phonecurl -s http://localhost:5000/health...". In Bash, `!!` is a shortcut for "repeat the last command", so Bash inserted my previous command into the text, even inside double quotes.
**Fix:** I put the JSON inside **single quotes** (`-d '{"text": "..."}'`). Bash does not expand `!!` inside single quotes.

## 14. "docker build" could not find the Dockerfile
**Problem:** `docker build -t sentiment140-api:v1 .` failed with "open Dockerfile: no such file or directory".
**Why:** I ran it from my home folder (`~`). The `.` at the end means "build from the current folder", and the Dockerfile is in the project folder.
**Fix:** I ran `cd ~/Downloads/"Data Engineering"/sentiment140-mlops` first, and the build worked.

## 15. The container disappeared from Docker Desktop
**Problem:** After `docker rm -f sentiment-api`, the container vanished from Docker Desktop.
**Why:** `docker rm` deletes the **container** (a running copy), but not the **image** (the package it was made from).
**Fix:** I started a new container from the same image with `docker run`. The image was still in the Images tab.

## 16. GitHub workflow file could not be created by the assistant tool
**Problem:** The tool I used to write files could not write into the `.github/` folder, because it is protected.
**Fix:** I moved the workflow file into `.github/workflows/` myself with one `mv` command in Git Bash.

## 17. Node.js 20 warnings in GitHub Actions
**Problem:** The first CI/CD run succeeded, but showed 2 warnings: "Node.js 20 is deprecated" for `actions/checkout@v4`, `actions/setup-python@v5` and `docker/login-action@v3`.
**Why:** These ready-made GitHub actions are written in JavaScript, and GitHub is moving its runners from Node.js 20 to Node.js 24. It already runs them on Node.js 24 automatically.
**Fix:** No action was needed. These are only warnings, and both jobs passed. In the future I would update the actions to their newest major versions.

## 18. The rollout history showed the same note twice
**Problem:** In the rollback demo, `kubectl rollout history` showed "release pinned image v1-220149e" next to every revision, even the original one.
**Why:** I added the change-cause note with `kubectl annotate` **before** changing the image. Kubernetes copied the note onto the version that was already running, and then onto the new one as well.
**Fix / lesson:** The rollback itself worked. `kubectl describe` showed the image back on `hirenpatel9/sentiment140-api:v1`, and `/health` answered throughout. Next time I will add the note **after** `kubectl set image`, or put the change-cause in `deployment.yaml` and use `kubectl apply`.

## 19. Warning about "kubectl apply" after the rollback
**Problem:** `kubectl rollout undo` printed a warning that the deployment "was previously managed with kubectl apply".
**Why:** Kubernetes remembers the last file I applied. A rollback changes the live deployment, but not that saved copy of the file.
**Fix / lesson:** After an emergency rollback, I also update `k8s/deployment.yaml` to match (Option D in MODEL_VERSIONING.md), so the next `kubectl apply` doesn't undo the rollback by accident.
