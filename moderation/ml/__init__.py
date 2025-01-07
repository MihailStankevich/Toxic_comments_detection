import tensorflow as tf
import pickle
import os
import joblib

# Load model and vectorizer
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    model_path = os.path.join(base_dir, 'svc11.pkl')  #сейчас это пайплайн который включает в себя и модель и векторайзер
    image_model_path = os.path.join(base_dir, 'spam_image_classifier_model11.h5')
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
        print("Text model loaded successfully.")
    image_model = tf.keras.models.load_model(image_model_path)
    print("Image model loaded successfully.")
    return model, image_model


model, image_model = load_model()