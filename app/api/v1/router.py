"""Aggregates every v1 route module."""

from fastapi import APIRouter

from app.api.v1.routes import assistant, chat, health, leads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(assistant.router)
api_router.include_router(leads.router)
