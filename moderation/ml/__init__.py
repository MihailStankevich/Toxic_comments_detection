
import pickle
import os

# Load model and vectorizer
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    model_path = os.path.join(base_dir, 'svc1.pkl')  #сейчас это пайплайн который включает в себя и модель и векторайзер
    vectorizer_path = os.path.join(base_dir, 'vectorizer.pkl') #эта строка не имеет смысла сейчас

    with open(vectorizer_path, 'rb') as f:
        vectorizer = pickle.load(f)
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    return model, vectorizer


model, vectorizer = load_model()