import os
import time
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import get_db
from ..db_models import Scan, ScanResult, ScanFeedback, ScanFeatures, FeedbackLabel

def build_training_dataset(db: Session, output_dir: str = "ml/datasets"):
    """
    Joins scans, scan_results, scan_features, and aggregated scan_feedback 
    to create a structured dataset for ML training.
    """
    # 1. Aggregate feedback to get the majority label per scan
    results = db.query(
        ScanFeedback.scan_id,
        ScanFeedback.label,
        func.count(ScanFeedback.id).label('count')
    ).group_by(ScanFeedback.scan_id, ScanFeedback.label).all()
    
    if not results:
        print("No feedback found. Cannot build training dataset.")
        return None
        
    aggregated = {}
    for scan_id, label, count in results:
        if scan_id not in aggregated:
            aggregated[scan_id] = []
        aggregated[scan_id].append({'label': label, 'count': count})
    
    scan_labels = {}
    for scan_id, feedback_list in aggregated.items():
        # Choose the label with the most votes
        majority = max(feedback_list, key=lambda x: x['count'])
        scan_labels[scan_id] = majority['label']
    
    # 2. Fetch associated features and scan results
    scan_ids = list(scan_labels.keys())
    
    # Join ScanFeatures and Scan (and ScanResult if needed)
    query = db.query(
        ScanFeatures.scan_id,
        ScanFeatures.features_json,
        Scan.url
    ).join(Scan, Scan.id == ScanFeatures.scan_id).filter(ScanFeatures.scan_id.in_(scan_ids))
    
    dataset_rows = []
    for scan_id, features_json, url in query:
        label = scan_labels[scan_id]
        
        row = {
            "scan_id": scan_id,
            "url": url,
            "label": label.value,
            **features_json
        }
        dataset_rows.append(row)
        
    if not dataset_rows:
        print("No scans with features found for the provided feedback.")
        return None
        
    df = pd.DataFrame(dataset_rows)
    
    # Ensure output directory exists (relative to the project root, assuming this runs from there)
    # Actually, let's use an absolute path or relative to project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    full_output_dir = os.path.join(project_root, output_dir)
    os.makedirs(full_output_dir, exist_ok=True)
    
    timestamp = int(time.time())
    file_name = f"{timestamp}.parquet"
    output_path = os.path.join(full_output_dir, file_name)
    
    df.to_parquet(output_path)
    print(f"Dataset successfully built: {output_path} ({len(df)} rows)")
    
    return output_path

if __name__ == "__main__":
    # For standalone testing if needed
    from ..db import SessionLocal
    db = SessionLocal()
    build_training_dataset(db)
