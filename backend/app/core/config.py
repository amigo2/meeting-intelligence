"""Central configuration, loaded from environment / .env.

12-factor: all config comes from the environment, so the same image runs locally
(docker-compose Postgres) and in production (Aurora Postgres) with no code change —
only DATABASE_URL differs.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS Bedrock (London / eu-west-2 for UK/EU data residency)
    aws_region: str = "eu-west-2"
    bedrock_llm_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"

    # Database (local docker-compose default; Aurora URL in prod)
    database_url: str = "postgresql://meetings:meetings@localhost:5432/meetings"


settings = Settings()
