import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import os

class URLDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = DistilBertTokenizer.from_pretrained("distilbert-base-uncased")
        
        if model_path and os.path.exists(model_path):
            print(f"Loading URL Detector from {model_path}")
            self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
        else:
            print("Loading base DistilBERT for URL Detector (Not Fine-Tuned)")
            self.model = DistilBertForSequenceClassification.from_pretrained("distilbert-base-uncased", num_labels=2)
        
        self.model.to(self.device)
        self.model.eval()

    def predict(self, url: str) -> float:
        """Returns probability of phishing (class 1)"""
        inputs = self.tokenizer(url, return_tensors="pt", truncation=True, max_length=128, padding="max_length")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
        return float(probs[0][1].item())
