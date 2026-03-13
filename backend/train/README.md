# Model Training Scripts

This directory contains scripts to train the deep learning models for the Phishing Detection System.

## Prerequisites
Ensure you have the required dependencies installed:
```bash
pip install -r ../requirements.txt
```

## 1. URL Transformer (DistilBERT)
Trains a DistilBERT model on URL strings.
- **Data**: `backend/data/url_dataset.csv` (Columns: `url`, `label`)
- **Run**: `python backend/train/train_url.py`
- **Output**: `backend/models/url_model/`

## 2. Visual Classifier (EfficientNet)
Trains an EfficientNet model on screenshots of websites.
- **Data**: `backend/data/visual_dataset.csv` (Columns: `image_path`, `label`)
- **Run**: `python backend/train/train_visual.py`
- **Output**: `backend/models/visual_model.pth`

## 3. HTML Classifier (CNN)
(Script to be added) Trains a CNN on raw HTML content.

## Note
These scripts assume you have prepared your datasets. If you don't have data yet, the system will run in "inference-only" mode using pre-trained base models (which won't be accurate for phishing but demonstrate the pipeline).
