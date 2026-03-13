import requests
import json

API_URL = "http://localhost:8000/api/predict"

# List of adversarial URLs (Obfuscated, Typosquatted, etc.)
ADVERSARIAL_CASES = [
    # 1. Typosquatting
    "http://g00gle.com",
    "http://paypa1.com",
    
    # 2. URL Shorteners (Simulated)
    "http://bit.ly/suspicious",
    
    # 3. Obfuscation
    "http://secure-login.update-verify.com/account",
    "http://192.168.1.1/login", # IP based
    
    # 4. Homograph Attack (Cyrillic 'a')
    "http://pаypal.com", 
    
    # 5. Excessive Subdomains
    "http://a.b.c.d.e.f.login.com"
]

def run_adversarial_test():
    print("--- Starting Adversarial Robustness Test ---")
    
    for url in ADVERSARIAL_CASES:
        try:
            res = requests.post(API_URL, json={"url": url})
            data = res.json()
            print(f"\nURL: {url}")
            print(f"Prediction: {data['prediction'].upper()}")
            print(f"Confidence: {data['confidence']}")
            print(f"Key Features: {data['explanation']['important_features']}")
        except Exception as e:
            print(f"Error testing {url}: {e}")

if __name__ == "__main__":
    run_adversarial_test()
