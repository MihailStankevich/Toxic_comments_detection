
import pickle
import os

# Load model and vectorizer
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current directory
    model_path = os.path.join(base_dir, 'cclf.pkl')  # Update to cclf.pkl
    vectorizer_path = os.path.join(base_dir, 'vectorizer.pkl')

    with open(vectorizer_path, 'rb') as f:
        vectorizer = pickle.load(f)
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model, vectorizer


model, vectorizer = load_model()