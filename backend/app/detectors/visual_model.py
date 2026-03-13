import torch
import torch.nn as nn
import timm
from PIL import Image
import io
import base64
import torchvision.transforms as transforms
import os

class VisualDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load EfficientNet-b0
        self.model = timm.create_model('efficientnet_b0', pretrained=True, num_classes=2)
        
        if model_path and os.path.exists(model_path):
            print(f"Loading Visual Detector from {model_path}")
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        else:
            print("Loading base EfficientNet for Visual Detector (Not Fine-Tuned)")
        
        self.model.to(self.device)
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def predict(self, screenshot_b64: str) -> float:
        """Returns probability of phishing (class 1) from base64 screenshot"""
        if not screenshot_b64:
            return 0.0
            
        try:
            # Remove header if present (e.g., "data:image/png;base64,...")
            if "," in screenshot_b64:
                screenshot_b64 = screenshot_b64.split(",")[1]
                
            image_data = base64.b64decode(screenshot_b64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            
            img_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(img_tensor)
                probs = torch.nn.functional.softmax(outputs, dim=-1)
                
            return float(probs[0][1].item())
        except Exception as e:
            print(f"Visual prediction error: {e}")
            return 0.0
