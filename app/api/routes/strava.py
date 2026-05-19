from fastapi import APIRouter, HTTPException, Body
from datetime import datetime
import logging
import json
from pathlib import Path
from typing import List, Any
from app.schemas.strava import (
    AnalysisResponse, UserTrainingData,
    BatchAnalysisResponse
)
from app.services.performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/strava", tags=["strava"])
analyzer = PerformanceAnalyzer()


@router.post("/analyze", response_model=BatchAnalysisResponse)
async def analyze_users(data: List[Any] = Body(...)):
    """
    POST - Analyze users from JSON array input
    
    Accepts:
    - Raw JSON array from data.json file content pasted directly
    - Or array of user training data objects
    """
    try:
        users_data = data
        
        # Ensure it's a list
        if not isinstance(users_data, list):
            raise HTTPException(status_code=400, detail="Input must be a JSON array of users")
        
        total_users = len(users_data)
        
        if total_users == 0:
            raise HTTPException(status_code=400, detail="No users found in input")
        
        logger.info(f"Starting analysis of {total_users} users from input")
        
        results = []
        errors = {}
        successful = 0
        failed = 0
        
        for user_data_dict in users_data:
            try:
                # Convert dict to UserTrainingData
                user_data = UserTrainingData(**user_data_dict)
                user_id = user_data.user_id
                
                # Run analysis
                result = analyzer.analyze(user_data)
                results.append(AnalysisResponse(**result))
                successful += 1
                
                logger.info(f"Analyzed user {user_id}")
                
            except Exception as e:
                failed += 1
                user_id = user_data_dict.get('user_id', 'unknown')
                error_msg = f"Error analyzing user {user_id}: {str(e)}"
                errors[user_id] = str(e)
                logger.error(error_msg)
                continue
        
        logger.info(f"Analysis complete: {successful} successful, {failed} failed")
        
        return BatchAnalysisResponse(
            total_users=total_users,
            successful=successful,
            failed=failed,
            results=results,
            errors=errors if errors else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


