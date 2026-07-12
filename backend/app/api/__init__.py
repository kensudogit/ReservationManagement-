from fastapi import APIRouter

from app.api import auth, billing, google, reservations, studios, subscriptions

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(studios.router)
api_router.include_router(reservations.router)
api_router.include_router(google.router)
api_router.include_router(subscriptions.router)
api_router.include_router(billing.router)
