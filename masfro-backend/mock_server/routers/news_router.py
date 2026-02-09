"""
Google News RSS-compatible mock endpoint.

Serves XML in RSS 2.0 format with RFC 2822 dates so that
AdvisoryScraperService.scrape_google_news_rss() can parse it
with zero logic changes.
"""

from fastapi import APIRouter, Query
from fastapi.responses import Response

from ..data_store import get_data_store

router = APIRouter()


@router.get("/news/rss")
async def news_rss_feed(
    q: str = Query("Marikina Flood"),
    hl: str = Query("en-PH"),
    gl: str = Query("PH"),
    ceid: str = Query("PH:en"),
):
    """
    Mock Google News RSS search endpoint.
    Returns RSS 2.0 XML with <channel><item> elements.
    Used by: AdvisoryScraperService.scrape_google_news_rss()
    """
    store = get_data_store()
    advisories = store.get_advisories()

    items_xml = ""
    for adv in advisories:
        title = _escape_xml(adv.get("title", ""))
        text = _escape_xml(adv.get("text", ""))
        pub_date = adv.get("pub_date", "")
        link = adv.get("link", "")

        items_xml += f"""    <item>
      <title>{title}</title>
      <description>{text}</description>
      <pubDate>{pub_date}</pubDate>
      <link>{link}</link>
    </item>
"""

    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Mock News RSS - {_escape_xml(q)}</title>
    <link>http://localhost:8081/news/rss</link>
    <description>Mock news feed for MAS-FRO simulation</description>
{items_xml}  </channel>
</rss>"""

    return Response(content=xml_content, media_type="application/rss+xml")


def _escape_xml(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
