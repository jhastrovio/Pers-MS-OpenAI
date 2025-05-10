import os
import joblib
import threading

# Paths to saved model and vectorizer
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../data/intent_classifier_model.joblib')
VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), '../data/intent_vectorizer.joblib')

# Singleton pattern for model/vectorizer loading
_model = None
_vectorizer = None
_lock = threading.Lock()

def load_model_and_vectorizer():
    global _model, _vectorizer
    with _lock:
        if _model is None or _vectorizer is None:
            _model = joblib.load(MODEL_PATH)
            _vectorizer = joblib.load(VECTORIZER_PATH)
    return _model, _vectorizer

def classify_intent(query: str) -> str:
    """
    Classify the intent of a user query as 'email', 'drive', 'mixed', or 'data'.
    """
    model, vectorizer = load_model_and_vectorizer()
    X = vectorizer.transform([query])
    return model.predict(X)[0]

# Example usage (for manual testing)
if __name__ == "__main__":
    test_query = "Show me my latest emails from Alice"
    print(f"Query: {test_query}")
    print(f"Predicted intent: {classify_intent(test_query)}") 