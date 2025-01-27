import os
import sys
sys.path.insert(0, '/tmp')
import django
from transformers import AutoModelForImageClassification, ViTImageProcessor, safetensors

# Set DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()

def reassemble_model(parts_dir, output_path):
    if not os.path.exists(output_path):
        with open(output_path, 'wb') as output_file:
            for part in sorted(os.listdir(parts_dir)):
                part_path = os.path.join(parts_dir, part)
                with open(part_path, 'rb') as part_file:
                    output_file.write(part_file.read())
        print(f"Reassembled model to {output_path}")
    else:
        print(f"Model already exists at {output_path}, skipping reassembly.")

# Call this function to reassemble the model file
model_parts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fine_tuned_model')
reassemble_model(model_parts_dir, os.path.join(model_parts_dir, 'model.safetensors'))

# Load models
def load_model():
    model_path = model_parts_dir
    model = AutoModelForImageClassification.from_pretrained(model_path, from_tf=False, torch_dtype=safetensors)
    processor = ViTImageProcessor.from_pretrained(model_path)
    print("Image model loaded successfully.")
    return model, processor

image_model, image_processor = load_model()
