from backend.routes.auth import router as auth_router
from backend.routes.profile import router as profile_router
from backend.routes.series import router as series_router
from backend.routes.ratings import router as ratings_router
from backend.routes.recommendation import router as recommendation_router

__all__ = [
    "auth_router",
    "profile_router",
    "series_router",
    "ratings_router",
    "recommendation_router",
]
