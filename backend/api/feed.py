from fastapi import APIRouter, Request, Response
from backend.core.dependencies import current_user
from backend.services.feed_service import feed, feed_publico

router = APIRouter()

@router.get("/api/feed")
def get_feed(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    user = current_user(request)
    return feed(user) if user else feed_publico()

@router.get("/api/public/feed")
def get_public_feed(response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return feed_publico()
