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
    image_model_path = os.path.join(base_dir, 'image_classifier_quantized.tflite')
    interpreter = tf.lite.Interpreter(model_path=image_model_path)
    interpreter.allocate_tensors()
    print("Image model loaded successfully.")
    return interpreter


image_model = load_model()