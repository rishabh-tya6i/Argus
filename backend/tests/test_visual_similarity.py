import pytest
import os
import asyncio
from app.db import SessionLocal
from app.model import ensure_model
from app.services.visual_similarity import visual_similarity_engine

# A tiny dummy image base64, essentially a 1x1 black pixel
DUMMY_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

def test_visual_impersonation_detection():
    # Attempt to load the ensemble model
    model = ensure_model()

    # Create DB Session
    db = SessionLocal()

    import torch
    
    # We generate an embedding for the dummy image
    test_tensor = visual_similarity_engine.generate_embedding(DUMMY_IMAGE_B64)
    if test_tensor is not None:
        visual_similarity_engine.cached_brands = [
            {"brand_name": "TestBrand", "legitimate_domain": "testbrand.com", "embedding": test_tensor}
        ]
    
    async def run_test():
        res = await model.predict(
            url="http://definitely-not-testbrand.com",
            html="<html><body><form><input type='password'></form></body></html>",
            screenshot=DUMMY_IMAGE_B64,
            db=db
        )
        
        assert res.prediction == "phishing"
        
        has_impersonation = False
        for r in res.explanation.reasons:
            if r.code == "BRAND_IMPERSONATION_DETECTED":
                has_impersonation = True
                assert "TestBrand" in r.message
        
        assert has_impersonation

    # Run the test
    asyncio.run(run_test())
    db.close()
