import os
import pickle
import torch
from torchvision import models

# Load models
def load_model():
    base_dir = os.path.dirname(os.path.abspath(__file__)) 

    # Load the text classification model (SVC pipeline)
    model_path = os.path.join(base_dir, 'svc_model86.pkl')  # Text model and vectorizer
    with open(model_path, 'rb') as f:
        text_model = pickle.load(f)
        print("Text model loaded successfully.")
    
    # Load the image classification model (PyTorch)
    image_model_path = os.path.join(base_dir, 'best_resnet18.pth')  # PyTorch model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Define the model architecture to match the saved model
    image_model = models.resnet18(pretrained=False)
    num_features = image_model.fc.in_features
    image_model.fc = torch.nn.Linear(num_features, 2)  # Binary classification
    image_model.load_state_dict(torch.load(image_model_path, map_location=device))
    image_model = image_model.to(device)
    image_model.eval()  # Set the model to evaluation mode
    print("Image model loaded successfully.")
    
    return text_model, image_model

# Initialize models
text_model, image_model = load_model()
