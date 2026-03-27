"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException
from ..models.user import User

router = APIRouter()

@router.post("/create-demo-user")
async def create_demo_user():
    """Create a demo user"""
    try:
        user = await User.create(username="demo_user")
        return {
            "status": "success",
            "message": "Demo user created successfully",
            "data": {
                "id": user.id,
                "username": user.username
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 