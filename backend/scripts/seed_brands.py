import io
import base64
import logging
from typing import List, Tuple

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal, init_db
from app.db_models import BrandTemplate
from app.services.visual_similarity import VisualSimilarityEngine

# Initialize DB (tables + extensions like pgvector)
init_db()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target brands to seed
BRANDS_TO_SEED = [
    {"name": "Microsoft", "domain": "microsoft.com", "category": "technology", "login": "login.microsoftonline.com"},
    {"name": "Google", "domain": "google.com", "category": "technology", "login": "accounts.google.com"},
    {"name": "Amazon Web Services", "domain": "aws.amazon.com", "category": "cloud", "login": "console.aws.amazon.com"},
    {"name": "PayPal", "domain": "paypal.com", "category": "finance", "login": "www.paypal.com/signin"},
    {"name": "Apple", "domain": "apple.com", "category": "technology", "login": "appleid.apple.com"},
    {"name": "GitHub", "domain": "github.com", "category": "technology", "login": "github.com/login"},
]

# Brand-specific colors (fallback dummy visuals)
COLORS: List[Tuple[int, int, int]] = [
    (0, 120, 212),   # Microsoft Blue
    (219, 68, 55),   # Google Red
    (255, 153, 0),   # AWS Orange
    (0, 48, 135),    # PayPal Blue
    (153, 153, 153), # Apple Grey
    (24, 23, 23),    # GitHub Black
]


def create_dummy_screenshot(color=(255, 0, 0)) -> str:
    """
    Creates a dummy 800x600 solid color image
    and returns its base64 representation.
    """
    img = Image.new("RGB", (800, 600), color=color)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def generate_embedding_with_retry(engine: VisualSimilarityEngine, image_b64: str, retries: int = 3):
    """
    Retry wrapper for embedding generation
    """
    for attempt in range(1, retries + 1):
        try:
            embedding = engine.generate_embedding(image_b64)

            if embedding and isinstance(embedding, list) and len(embedding) > 0:
                return embedding

            logger.warning(f"Invalid embedding received (attempt {attempt})")

        except Exception as e:
            logger.error(f"Embedding generation failed (attempt {attempt}): {e}")

    return None


def seed_brands(db: Session, engine: VisualSimilarityEngine):
    """
    Core seeding logic
    """
    new_entries = []

    for i, brand in enumerate(BRANDS_TO_SEED):
        logger.info(f"[{i+1}/{len(BRANDS_TO_SEED)}] Processing '{brand['name']}'")

        # Check if already exists
        existing = db.query(BrandTemplate).filter(
            BrandTemplate.brand_name == brand["name"]
        ).first()

        if existing:
            logger.info(f"Skipping '{brand['name']}' (already exists)")
            continue

        # Generate dummy screenshot (replace with real screenshot in future)
        dummy_b64 = create_dummy_screenshot(COLORS[i % len(COLORS)])

        # Generate embedding with retry
        embedding = generate_embedding_with_retry(engine, dummy_b64)

        if not embedding:
            logger.error(f"Failed to generate embedding for '{brand['name']}'")
            continue

        new_entries.append(
            BrandTemplate(
                brand_name=brand["name"],
                legitimate_domain=brand["domain"],
                embedding_vector=embedding,
                category=brand["category"],
                login_url=brand["login"]
            )
        )

    if not new_entries:
        logger.info("No new brands to insert.")
        return

    logger.info(f"Inserting {len(new_entries)} new brands...")

    db.add_all(new_entries)

    try:
        db.commit()
        logger.info("Seeding completed successfully.")
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error during commit: {e}")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during commit: {e}")
        raise


def main():
    logger.info("Starting brand seeding process...")

    engine = VisualSimilarityEngine()

    with SessionLocal() as db:
        seed_brands(db, engine)

    logger.info("Brand seeding finished.")


if __name__ == "__main__":
    main()
