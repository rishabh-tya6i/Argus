import time
import os
import schedule
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..ml.feedback_service import FeedbackIngestionService
from ..ml.train import TrainingPipeline

# Threshold for retraining
RETRAIN_THRESHOLD = 50

def run_pipeline():
    """
    Main background job for Argus ML Pipeline.
    1. Ingest feedback into training dataset.
    2. Check if new data warrants retraining.
    3. Train and register new model.
    """
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting ML Pipeline Worker...")
    db = SessionLocal()
    try:
        # 1. Ingestion Layer
        ingester = FeedbackIngestionService(db)
        new_entries = ingester.process_new_feedback()
        print(f"Ingested {new_entries} new feedback entries into TrainingDataset.")
        
        # 2. Check if retraining is needed
        # We can also check time since last training
        if new_entries >= RETRAIN_THRESHOLD:
            print(f"Retrain threshold {RETRAIN_THRESHOLD} reached. Starting retraining...")
            pipeline = TrainingPipeline(db)
            metadata = pipeline.run()
            if metadata:
                print(f"ML Pipeline completed: New model version {metadata['version']} created.")
        else:
            print("Not enough new data for retraining. Skipping for now.")
            
    except Exception as e:
        print(f"Error in ML pipeline worker: {str(e)}")
    finally:
        db.close()

def main():
    """
    Worker entry point (cron or daemon mode).
    """
    # Run once at startup
    run_pipeline()
    
    # Schedule every day at UTC 02:00 (mid-night) or periodically
    schedule.every(24).hours.do(run_pipeline)
    
    print("Argus ML Pipeline Worker is running. Scheduled for daily job...")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()
