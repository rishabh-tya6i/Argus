import torch
import torch.nn as nn
import torch.nn.functional as F
import os
from bs4 import BeautifulSoup

class HTMLCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_classes):
        super(HTMLCNN, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.conv1 = nn.Conv1d(embed_dim, 128, kernel_size=5)
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.embedding(x) # (batch, seq, embed)
        x = x.permute(0, 2, 1) # (batch, embed, seq)
        x = F.relu(self.conv1(x))
        x = self.pool(x).squeeze(2)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x

class HTMLDetector:
    def __init__(self, model_path: str = None):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.vocab_size = 5000
        self.max_len = 1000
        
        self.model = HTMLCNN(self.vocab_size, 64, 2)
        
        if model_path and os.path.exists(model_path):
            print(f"Loading HTML Detector from {model_path}")
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        else:
            print("Initialized fresh HTML Detector (Random Weights)")
        
        self.model.to(self.device)
        self.model.eval()

    def preprocess(self, html: str):
        # Simple hashing vectorizer simulation for demo
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text()
        # Simple char-level-ish hashing
        tokens = [hash(w) % self.vocab_size for w in text.split()][:self.max_len]
        if len(tokens) < self.max_len:
            tokens += [0] * (self.max_len - len(tokens))
        return torch.tensor([tokens], dtype=torch.long).to(self.device)

    def predict(self, html: str) -> float:
        """Returns probability of phishing (class 1)"""
        if not html:
            return 0.0
            
        try:
            input_tensor = self.preprocess(html)
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probs = torch.nn.functional.softmax(outputs, dim=-1)
            return float(probs[0][1].item())
        except Exception as e:
            print(f"HTML prediction error: {e}")
            return 0.0
