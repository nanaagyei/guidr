"""Custom middlewares for Scrapy spiders."""
from scrapy import signals


class UserAgentMiddleware:
    """Ensures a consistent user agent."""

    def __init__(self, user_agent: str):
        self.user_agent = user_agent

    @classmethod
    def from_crawler(cls, crawler):
        return cls(user_agent=crawler.settings.get("USER_AGENT", "GuidrBot/1.0"))

    def process_request(self, request, spider):
        request.headers.setdefault(b"User-Agent", self.user_agent)

