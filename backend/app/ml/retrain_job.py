import logging
from .dataset_builder import build_training_dataset
from .train import train_and_evaluate, register_model_version
from ..db import SessionLocal
from ..observability import ML_TRAINING_RUNS_TOTAL, ML_TRAINING_FAILURES_TOTAL, ML_MODEL_ACCURACY

logger = logging.getLogger(__name__)

def run_retrain_loop():
    """
    Orchestrates the full feedback loop: 
    1. Aggregates analyst feedback and extracted features.
    2. Builds a new training dataset.
    3. Trains a new model version.
    4. Evaluates and registers it in the Model Registry.
    """
    db = SessionLocal()
    model_name = "ensemble"
    
    try:
        logger.info("Starting automated ML retraining cycle...")
        ML_TRAINING_RUNS_TOTAL.labels(model_name=model_name).inc()
        
        # 1. Build Dataset
        dataset_path = build_training_dataset(db)
        if not dataset_path:
            logger.warning("Retraining aborted: Insufficient feedback data to build dataset.")
            return
            
        # 2. Train & Evaluate
        results = train_and_evaluate(dataset_path, model_name=model_name)
        
        if results:
            # 3. Register 
            version_id = register_model_version(db, results)
            
            # 4. Update Metrics 
            ML_MODEL_ACCURACY.labels(model_name=model_name).set(results["metrics"]["accuracy"])
            
            logger.info(f"Successfully completed retraining. New version: {results['version']} (ID: {version_id})")
        else:
            logger.error("Training failed to produce valid artifacts.")
            ML_TRAINING_FAILURES_TOTAL.labels(model_name=model_name).inc()
            
    except Exception as exc:
        logger.exception(f"Critical failure in retraining job: {exc}")
        ML_TRAINING_FAILURES_TOTAL.labels(model_name=model_name).inc()
    finally:
        db.close()

if __name__ == "__main__":
    run_retrain_loop()
 Wilde
