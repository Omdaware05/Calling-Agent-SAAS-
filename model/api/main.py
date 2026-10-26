import time
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from classifier.engine import IntentClassifier
from classifier.models import (
    ClassifyRequest,
    BatchClassifyRequest,
    BatchClassifyResponse,
    StrictClassificationResponse,
    DetailedClassificationResponse,
    IntentClassification,
)

app = FastAPI(
    title="AI Call Transcript Intent Classifier",
    description="High-Recall Multilingual Two-Class Intent Classifier (INTERESTED vs NOT_INTERESTED)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

classifier = IntentClassifier()

# In-memory statistics
STATS = {
    "total_classified": 0,
    "interested_count": 0,
    "not_interested_count": 0,
    "start_time": time.time()
}

@app.post(
    "/classify",
    response_model=Any,
    summary="Classify a single call transcript",
    description="Returns strict { 'classification': 'INTERESTED' } by default, or detailed diagnostics if explain=true."
)
async def classify_transcript(request: ClassifyRequest):
    if not request.transcript or not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty.")

    if request.explain:
        result = classifier.classify_detailed(request.transcript)
        STATS["total_classified"] += 1
        if result.classification == IntentClassification.INTERESTED:
            STATS["interested_count"] += 1
        else:
            STATS["not_interested_count"] += 1
        return result
    else:
        strict_res = classifier.classify_strict(request.transcript)
        STATS["total_classified"] += 1
        if strict_res["classification"] == "INTERESTED":
            STATS["interested_count"] += 1
        else:
            STATS["not_interested_count"] += 1
        return strict_res

@app.post(
    "/classify/batch",
    response_model=BatchClassifyResponse,
    summary="Batch classify multiple call transcripts"
)
async def classify_batch(request: BatchClassifyRequest):
    if not request.transcripts:
        raise HTTPException(status_code=400, detail="Transcripts list cannot be empty.")

    results = []
    interested_count = 0
    not_interested_count = 0

    for t in request.transcripts:
        if request.explain:
            res = classifier.classify_detailed(t)
            results.append(res)
            if res.classification == IntentClassification.INTERESTED:
                interested_count += 1
            else:
                not_interested_count += 1
        else:
            res = classifier.classify_strict(t)
            results.append(res)
            if res["classification"] == "INTERESTED":
                interested_count += 1
            else:
                not_interested_count += 1

    STATS["total_classified"] += len(request.transcripts)
    STATS["interested_count"] += interested_count
    STATS["not_interested_count"] += not_interested_count

    return BatchClassifyResponse(
        results=results,
        total=len(request.transcripts),
        interested_count=interested_count,
        not_interested_count=not_interested_count
    )

@app.get("/health", summary="Health check")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Call Transcript Intent Classifier",
        "version": "1.0.0",
        "supported_languages": ["English", "Hindi", "Marathi", "Hinglish", "Marathish", "Code-Switching"],
        "classification_classes": ["INTERESTED", "NOT_INTERESTED"]
    }

@app.get("/metrics", summary="Service usage statistics")
async def get_metrics():
    total = STATS["total_classified"]
    lead_rate = (STATS["interested_count"] / total * 100) if total > 0 else 0.0
    return {
        "uptime_seconds": int(time.time() - STATS["start_time"]),
        "total_classified": total,
        "interested_count": STATS["interested_count"],
        "not_interested_count": STATS["not_interested_count"],
        "lead_preservation_rate_percent": round(lead_rate, 2)
    }

@app.get("/", summary="API landing page")
async def api_root():
    return {"message": "Classifier API active. Visit /docs for Swagger documentation."}
