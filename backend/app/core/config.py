"""Central configuration, loaded from environment / .env.

12-factor: all config comes from the environment, so the same image runs locally
(docker-compose Postgres) and in production (Aurora Postgres) with no code change —
only DATABASE_URL differs.
"""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Also load .env into os.environ so boto3's default credential chain (AWS_*) sees it.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS Bedrock (London / eu-west-2 for UK/EU data residency)
    aws_region: str = "eu-west-2"
    bedrock_llm_model_id: str = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
    bedrock_embed_model_id: str = "amazon.titan-embed-text-v2:0"
    embed_dim: int = 1024  # Titan Text Embeddings V2 output size -> pgvector column size

    # Database (local docker-compose default; Aurora URL in prod)
    database_url: str = "postgresql://meetings:meetings@localhost:5432/meetings"


settings = Settings()
