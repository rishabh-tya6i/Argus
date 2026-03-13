import os
import io
import base64
import asyncio
from PIL import Image
from sqlalchemy.orm import Session
from app.db import SessionLocal, init_db
from app.db_models import BrandTemplate
from app.services.visual_similarity import VisualSimilarityEngine

# Create tables and pgvector extension if needed
init_db()

# Target brands to seed
BRANDS_TO_SEED = [
    {"name": "Microsoft", "domain": "microsoft.com", "category": "technology", "login": "login.microsoftonline.com"},
    {"name": "Google", "domain": "google.com", "category": "technology", "login": "accounts.google.com"},
    {"name": "Amazon Web Services", "domain": "aws.amazon.com", "category": "cloud", "login": "console.aws.amazon.com"},
    {"name": "PayPal", "domain": "paypal.com", "category": "finance", "login": "www.paypal.com/signin"},
    {"name": "Apple", "domain": "apple.com", "category": "technology", "login": "appleid.apple.com"},
    {"name": "GitHub", "domain": "github.com", "category": "technology", "login": "github.com/login"},
]

def create_solid_color_dummy_screenshot(color=(255, 0, 0)) -> str:
    """Creates a dummy 800x600 solid color image and returns its base64 representation."""
    img = Image.new("RGB", (800, 600), color=color)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

async def main():
    engine = VisualSimilarityEngine()
    db: Session = SessionLocal()
    
    try:
        colors = [
            (0, 120, 212),   # Microsoft Blue
            (219, 68, 55),   # Google Red
            (255, 153, 0),   # AWS Orange
            (0, 48, 135),    # PayPal Blue
            (153, 153, 153), # Apple Grey
            (24, 23, 23),    # GitHub Black
        ]
        
        for i, brand in enumerate(BRANDS_TO_SEED):
            # Check if brand already exists
            existing = db.query(BrandTemplate).filter(BrandTemplate.brand_name == brand["name"]).first()
            if existing:
                print(f"Brand '{brand['name']}' already exists. Skipping.")
                continue
                
            print(f"Generating embedding for '{brand['name']}'...")
            
            # Use dummy image for seeding
            dummy_screenshot_b64 = create_solid_color_dummy_screenshot(color=colors[i % len(colors)])
            
            embedding = engine.generate_embedding(dummy_screenshot_b64)
            
            if embedding is None:
                print(f"Failed to generate embedding for '{brand['name']}'.")
                continue
                
            new_brand = BrandTemplate(
                brand_name=brand["name"],
                legitimate_domain=brand["domain"],
                embedding_vector=embedding,
                category=brand["category"],
                login_url=brand["login"]
            )
            
            db.add(new_brand)
            db.commit()
            print(f"Successfully seeded '{brand['name']}'.")
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
