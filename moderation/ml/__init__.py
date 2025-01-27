import os
import sys
sys.path.insert(0, '/tmp')
import django
from transformers import AutoModelForImageClassification, ViTImageProcessor
from safetensors import safe_open
import torch

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

# Ensure the directory with model parts exists
model_parts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fine_tuned_model')
model_output_path = os.path.join(model_parts_dir, 'model.safetensors')
reassemble_model(model_parts_dir, model_output_path)

# Load models
def load_model():
    config_path = os.path.join(model_parts_dir, 'config.json')
    preprocessor_config_path = os.path.join(model_parts_dir, 'preprocessor_config.json')
    model_weights_path = model_output_path

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    # Load the model configuration and weights
    model = AutoModelForImageClassification.from_pretrained(
        model_weights_path, 
        config=config_path, 
        from_tf=False, 
        torch_dtype=torch.float32
    )

    # Load the processor configuration
    processor = ViTImageProcessor.from_pretrained(preprocessor_config_path)
    print("Image model loaded successfully.")
    return model, processor

image_model, image_processor = load_model()
