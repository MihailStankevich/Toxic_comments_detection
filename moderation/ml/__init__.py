import tensorflow as tf
import sklearn
import pickle
import os
import django
# Set DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()

# Load model and vectorizer
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    model_path = os.path.join(base_dir, 'cclfnew.pkl') 
    vectorizer_path = os.path.join(base_dir, 'vectorizernew.pkl')
    image_model_path = os.path.join(base_dir, 'updated_model22.h5')
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
        print("Text model loaded successfully.")
    with open(vectorizer_path, 'rb') as f:
        vectorizer = pickle.load(f)
        print("Vectorizer loaded successfully.")
    image_model = tf.keras.models.load_model(image_model_path)
    print("Image model loaded successfully.")
    return model, image_model, vectorizer


model, image_model, vectorizer = load_model()