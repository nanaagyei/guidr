"""Configuration settings for Guidr backend."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    
    # JWT
    jwt_secret: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Environment
    env: str = "development"
    
    # Object Storage (for future use)
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    
    # Email configuration (for 2FA)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None  # Gmail address
    smtp_password: Optional[str] = None  # Gmail app password
    email_from: str = "Guidr <no-reply@guidr.app>"
    app_public_url: str = "https://guidr.app"  # Base URL for logo in emails

    # Third-party integrations / APIs
    college_scorecard_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    firecrawl_api_key: Optional[str] = None

    # Search (Meilisearch)
    meilisearch_host: str = "http://localhost:7700"
    meilisearch_master_key: Optional[str] = None
    meilisearch_index_prefix: str = "guidr"

    # Scraper defaults
    scraper_user_agent: str = "GuidrBot/1.0 (+https://guidr.app)"
    scraper_delay_seconds: float = 1.0
    program_delay_seconds: float = 1.0  # Delay between program collection requests
    scraper_max_retries: int = 3

    # LLM extraction flags
    enable_llm_extraction: bool = True
    llm_extraction_model: str = "llama-3.1-8b-instant"  # Use same model as link selection for reliability
    llm_validation_model: Optional[str] = None

    # Embeddings
    embedding_provider: str = "sentence-transformers"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Google Search (optional, for finding school websites)
    google_search_enabled: bool = True
    google_search_api_key: Optional[str] = None
    
    # Playwright
    playwright_browser: str = "headless"  # headless, chromium, firefox
    playwright_timeout: int = 30000
    
    # Firecrawl
    firecrawl_extraction_schema: bool = True  # Use structured extraction
    
    # Perplexity (Research Gateway)
    perplexity_api_key: Optional[str] = None
    research_max_concurrent: int = 3

    # Agent Settings
    agent_max_steps: int = 10
    agent_retry_attempts: int = 3

    # MinIO / Data Lake Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "guidr-data-lake"
    minio_secure: bool = False

    # Pipeline Settings
    scrape_rate_limit_per_minute: int = 15
    scrape_concurrent_domains: int = 5
    scrape_off_peak_start_hour: int = 2
    scrape_off_peak_end_hour: int = 6
    pipeline_env: str = "development"
    use_scraping_orchestrator: bool = True  # Use centralized URL discovery
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()

