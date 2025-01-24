import tensorflow as tf
import pickle
import os
import django
# Set DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()

# Load model and vectorizer
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__)) 
    image_model_path = os.path.join(base_dir, 'image_classifier_tf.h5')
    image_model = tf.keras.models.load_model(image_model_path)
    print("Image model loaded successfully.")
    return image_model


image_model = load_model()