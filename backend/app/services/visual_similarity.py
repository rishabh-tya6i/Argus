import logging
import io
import base64
from typing import Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db_models import BrandTemplate

logger = logging.getLogger(__name__)

class VisualSimilarityEngine:
    """
    Engine to detect brand impersonation via screenshot similarity.
    Uses open_clip (ViT-B-32) to generate 512-dimensional embeddings.
    """
    def __init__(self):
        self.device = None
        self.model = None
        self.preprocess = None
        self.cached_brands = []
        self._initialized = False

    def _initialize_model(self):
        if self._initialized:
            return

        try:
            import torch
            import open_clip

            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"VisualSimilarityEngine initializing CLIP model (ViT-B-32) on {self.device}...")
            
            # Load CLIP ViT-B/32 model and preprocessing pipeline
            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                'ViT-B-32', pretrained='laion2b_s34b_b79k', device=self.device
            )
            self.model.eval()
            self._initialized = True
            logger.info("VisualSimilarityEngine successfully initialized CLIP.")
        except ImportError as e:
            logger.error(f"Failed to import required visual libraries: {e}")
            self._initialized = False
        except Exception as e:
            logger.error(f"Error loading CLIP model: {e}")
            self._initialized = False

    def load_cache(self, db: Session):
        """Loads all brand templates into memory for fast comparison."""
        try:
            from pgvector.sqlalchemy import Vector
            brands = db.execute(select(BrandTemplate)).scalars().all()
            self.cached_brands = brands
            logger.info(f"VisualSimilarityEngine loaded {len(self.cached_brands)} brand templates into cache.")
        except Exception as e:
            logger.error(f"Error loading brand templates cache: {e}")

    def generate_embedding(self, screenshot_b64: str) -> Optional[list[float]]:
        """
        Generates a 512-d normalized embedding vector from a base64 screenshot.
        Includes preprocessing (resize, crop, normalize, to_tensor).
        """
        if not screenshot_b64:
            return None

        self._initialize_model()
        if not self._initialized:
            return None

        import torch
        from PIL import Image

        try:
            # Handle base64 header if present
            if "," in screenshot_b64:
                screenshot_b64 = screenshot_b64.split(",")[1]

            image_data = base64.b64decode(screenshot_b64)
            image = Image.open(io.BytesIO(image_data)).convert("RGB")

            # Apply open_clip preprocessing pipeline
            # (Resize, CenterCrop, Normalize, ToTensor)
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                # Extract image features
                image_features = self.model.encode_image(image_tensor)
                
                # Normalize features for cosine similarity
                image_features /= image_features.norm(dim=-1, keepdim=True)
                
            return image_features[0].cpu().numpy().tolist()

        except Exception as e:
            logger.error(f"Visual embedding generation failed: {e}")
            return None

    def detect_impersonation(
        self, screenshot_b64: str, target_url: str, similarity_threshold: float = 0.85
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detects if a given screenshot visually impersonates a stored brand.
        Rules: Similarity > threshold AND target_url domain != brand.legitimate_domain.
        """
        if not self.cached_brands:
            return False, None

        embedding = self.generate_embedding(screenshot_b64)
        if not embedding:
            return False, None

        import torch
        embedding_tensor = torch.tensor(embedding)

        highest_sim = -1.0
        detected_brand = None

        from urllib.parse import urlparse
        
        try:
            parsed_target = urlparse(target_url)
            target_domain = parsed_target.netloc.lower()
            # simple strip for www
            if target_domain.startswith("www."):
                target_domain = target_domain[4:]
        except Exception:
            target_domain = ""

        for brand in self.cached_brands:
            brand_vec = brand.embedding_vector
            if not brand_vec:
                continue
            
            brand_tensor = torch.tensor(brand_vec)
            
            # Compute cosine similarity
            sim = torch.nn.functional.cosine_similarity(embedding_tensor.unsqueeze(0), brand_tensor.unsqueeze(0)).item()
            
            if sim > highest_sim:
                highest_sim = sim
                detected_brand = brand

        if highest_sim > similarity_threshold and detected_brand:
            # Domain check: The brand should not be legitimately hosting this
            legit_domain = detected_brand.legitimate_domain.lower()
            
            # If target domain ends with legitimate domain, it's safe (e.g. login.microsoft.com ends with microsoft.com)
            if legit_domain in target_domain:
                return False, None
                
            return True, {
                "brand_name": detected_brand.brand_name,
                "similarity_score": round(highest_sim, 4),
                "threshold_used": similarity_threshold
            }

        return False, None

# Singleton instance
visual_similarity_engine = VisualSimilarityEngine()
