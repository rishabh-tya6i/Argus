from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class PredictRequest(BaseModel):
    url: str
    html: Optional[str] = None
    screenshot: Optional[str] = None  # Base64 encoded image string
    source: Optional[str] = None  # extension/cli/sdk/dashboard/other


class ModelScores(BaseModel):
    url_model: float
    html_model: float
    visual_model: float
    classical_model: float


class ExplanationReason(BaseModel):
    code: str
    category: str
    weight: float
    message: str


class Explanation(BaseModel):
    model_scores: ModelScores
    important_features: List[str]
    reasons: List[ExplanationReason] = Field(default_factory=list)


class PredictResponse(BaseModel):
    prediction: str
    confidence: float
    explanation: Explanation


class BatchPredictRequest(BaseModel):
    urls: List[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str


class MetricsResponse(BaseModel):
    accuracy: float
    precision: float
    recall: float
    f1: float


class EmailScanResponse(BaseModel):
    id: int
    email_id: str
    subject: Optional[str]
    sender: Optional[str]
    scan_id: int
    detection_result: str
    risk_score: float
    created_at: datetime


class SyncGmailRequest(BaseModel):
    user_id: int
