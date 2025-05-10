import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib
import os

# Paths
DATA_PATH = "data/intent_training_data.csv"
MODEL_PATH = "data/intent_classifier_model.joblib"
VECTORIZER_PATH = "data/intent_vectorizer.joblib"

# 1. Load dataset
data = pd.read_csv(DATA_PATH)
print("Columns:", data.columns.tolist())
X = data["text"]
y = data["label"]

# 2. Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Vectorize text
vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# 4. Train classifier
model = LogisticRegression(max_iter=1000)
model.fit(X_train_vec, y_train)

# 5. Evaluate
y_pred = model.predict(X_test_vec)
print(classification_report(y_test, y_pred))

# 6. Save model and vectorizer
os.makedirs("data", exist_ok=True)
joblib.dump(model, MODEL_PATH)
joblib.dump(vectorizer, VECTORIZER_PATH)
print(f"Model saved to {MODEL_PATH}")
print(f"Vectorizer saved to {VECTORIZER_PATH}")
