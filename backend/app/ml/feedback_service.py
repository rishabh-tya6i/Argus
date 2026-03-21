from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from ..db_models import Scan, ScanFeedback, TrainingDataset, User, UserRole, FeedbackLabel, ScanFeatures
from .feature_extractor import FeatureExtractor

class FeedbackIngestionService:
    """
    Ingests and processes raw feedback into a clean training dataset.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.extractor = FeatureExtractor()
        self.role_confidence = {
            UserRole.admin: 1.0,
            UserRole.engineer: 0.95,
            UserRole.analyst: 0.90,
            UserRole.viewer: 0.50
        }

    def process_new_feedback(self) -> int:
        """
        Processes unprocessed feedback and updates the TrainingDataset table.
        """
        # Find scans that have feedback but aren't in TrainingDataset yet
        # For simplicity, we'll process scans where feedback was updated since the last run
        # or where training_dataset doesn't have an entry for the scan.
        
        # 1. Fetch all unique scan_ids from ScanFeedback not in TrainingDataset
        processed_scans = self.db.query(TrainingDataset.scan_id).filter(TrainingDataset.scan_id.isnot(None)).all()
        processed_scan_ids = [s[0] for s in processed_scans]
        
        pending_scans = self.db.query(ScanFeedback.scan_id).distinct().filter(
            ScanFeedback.scan_id.notin_(processed_scan_ids)
        ).all()
        
        new_entries_count = 0
        for (scan_id,) in pending_scans:
            # 2. Get all feedback for this scan
            feedbacks = self.db.query(ScanFeedback, User).join(User, User.id == ScanFeedback.analyst_user_id).filter(
                ScanFeedback.scan_id == scan_id
            ).all()
            
            if not feedbacks:
                continue
                
            # 3. Determine consensus label and confidence
            label_scores = {
                FeedbackLabel.safe: 0.0,
                FeedbackLabel.suspicious: 0.0,
                FeedbackLabel.phishing: 0.0
            }
            
            for fb, user in feedbacks:
                weight = self.role_confidence.get(user.role, 0.7)
                label_scores[fb.label] += weight
            
            # Majority wins
            consensus_label = max(label_scores, key=label_scores.get)
            total_score = sum(label_scores.values())
            confidence = label_scores[consensus_label] / total_score if total_score > 0 else 0.0
            
            # 4. Extract features
            scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                continue
            
            # Use cached features if available, else extract
            cached_features = self.db.query(ScanFeatures).filter(ScanFeatures.scan_id == scan_id).first()
            if cached_features:
                features = cached_features.features_json
            else:
                # We need HTML for better features, but let's assume URL at least
                features = self.extractor.extract_all(scan.url)
            
            # 5. Save to TrainingDataset
            dataset_entry = TrainingDataset(
                scan_id=scan_id,
                features=features,
                label=consensus_label,
                confidence=confidence,
                source="analyst_feedback"
            )
            self.db.add(dataset_entry)
            new_entries_count += 1
            
        self.db.commit()
        return new_entries_count

    def get_dataset_stats(self) -> dict:
        """
        Returns stats about the current training dataset.
        """
        stats = self.db.query(
            TrainingDataset.label, 
            func.count(TrainingDataset.id)
        ).group_by(TrainingDataset.label).all()
        
        return {label.value: count for label, count in stats}
