"""
Social media mock endpoints.

Serves both HTML (for BeautifulSoup scraping) and JSON API (for direct fetch)
so that the new SocialScraperService can use either method.
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from ..data_store import get_data_store

router = APIRouter()


@router.get("/social/feed", response_class=HTMLResponse)
async def social_feed():
    """
    Mock social media feed as HTML page.
    Structure: article.tweet[data-tweet-id] with child elements.
    Used by: SocialScraperService.scrape_feed() (BS4)
    """
    store = get_data_store()
    posts = store.get_social_posts()

    articles = ""
    for post in posts:
        tweet_id = post.get("tweet_id", "")
        username = post.get("username", "")
        text = post.get("text", "")
        timestamp = post.get("timestamp", "")
        image_path = post.get("image_path", "")

        media_html = ""
        if image_path:
            media_html = f'<div class="tweet-media"><img src="{image_path}" alt="tweet media"></div>'

        articles += f"""<article class="tweet" data-tweet-id="{tweet_id}">
    <span class="username">@{username}</span>
    <time class="timestamp" datetime="{timestamp}">{timestamp}</time>
    <div class="tweet-text">{text}</div>
    {media_html}
</article>
"""

    html = f"""<!DOCTYPE html>
<html>
<head><title>Social Feed</title></head>
<body>
<div class="feed">
{articles}
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/social/api/tweets")
async def tweets_api(
    limit: int = Query(50, ge=1, le=200),
    since: str = Query(None),
):
    """
    Mock social media JSON API.
    Returns tweets in the scout_tweets format.
    Used by: SocialScraperService.fetch_tweets_api()
    """
    store = get_data_store()
    posts = store.get_social_posts(limit=limit, since=since)
    return {"tweets": posts, "count": len(posts)}
