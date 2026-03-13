import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import os
from bs4 import BeautifulSoup

# Configuration
DATA_CSV = "backend/data/html_dataset.csv" # CSV with 'html' and 'label'
MODEL_SAVE_PATH = "backend/models/html_model.pth"
EPOCHS = 5
BATCH_SIZE = 16
VOCAB_SIZE = 5000
MAX_LEN = 1000

class HTMLDataset(Dataset):
    def __init__(self, df):
        self.df = df

    def __len__(self):
        return len(self.df)

    def preprocess(self, html):
        soup = BeautifulSoup(str(html), "html.parser")
        text = soup.get_text()
        tokens = [hash(w) % VOCAB_SIZE for w in text.split()][:MAX_LEN]
        if len(tokens) < MAX_LEN:
            tokens += [0] * (MAX_LEN - len(tokens))
        return torch.tensor(tokens, dtype=torch.long)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        html = row['html']
        label = row['label']
        return self.preprocess(html), torch.tensor(label, dtype=torch.long)

class HTMLCNN(nn.Module):
    def __init__(self, vocab_size, embed_dim, num_classes):
        super(HTMLCNN, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.conv1 = nn.Conv1d(embed_dim, 128, kernel_size=5)
        self.pool = nn.AdaptiveMaxPool1d(1)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.embedding(x)
        x = x.permute(0, 2, 1)
        x = torch.relu(self.conv1(x))
        x = self.pool(x).squeeze(2)
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x

def train():
    if not os.path.exists(DATA_CSV):
        print(f"Dataset CSV not found at {DATA_CSV}.")
        return

    df = pd.read_csv(DATA_CSV)
    dataset = HTMLDataset(df)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = HTMLCNN(VOCAB_SIZE, 64, 2)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print("Starting training...")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            total_loss += loss.item()
            loss.backward()
            optimizer.step()
            
        print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {total_loss/len(loader)}")

    print(f"Saving model to {MODEL_SAVE_PATH}")
    torch.save(model.state_dict(), MODEL_SAVE_PATH)

if __name__ == "__main__":
    train()
