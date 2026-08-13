"""AWS Bedrock client — embeddings (Titan) and, later, generation (Claude).

All model calls stay in-AWS (London, EU inference profile), so data doesn't leave
the EU. Credentials come from the standard AWS chain (env vars loaded from .env, or
~/.aws) — never hardcoded here.
"""

import json

import boto3

from app.core.config import settings

# One shared bedrock-runtime client, created lazily so importing this module
# never requires AWS credentials (keeps unit tests / tooling credential-free).
_client = None


def _bedrock():
    global _client
    if _client is None:
        _client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    return _client


def embed_text(text: str) -> list[float]:
    """Embed one string with Titan Text Embeddings V2.

    Returns a `embed_dim`-length vector (1024). `normalize=True` unit-normalises the
    vector, which pairs cleanly with cosine similarity in pgvector.
    """
    response = _bedrock().invoke_model(
        modelId=settings.bedrock_embed_model_id,
        body=json.dumps(
            {"inputText": text, "dimensions": settings.embed_dim, "normalize": True}
        ),
    )
    payload = json.loads(response["body"].read())
    return payload["embedding"]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed many strings. Titan embeds one input per call, so we loop."""
    return [embed_text(t) for t in texts]


def generate(system_prompt: str, user_prompt: str, max_tokens: int = 1000,
             temperature: float = 0.0) -> str:
    """Generate text with Claude via Bedrock's Converse API.

    Converse is Bedrock's unified, model-agnostic chat API — it works with the EU
    inference profile and keeps the message format simple. temperature=0 for
    deterministic, grounded answers.
    """
    response = _bedrock().converse(
        modelId=settings.bedrock_llm_model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return response["output"]["message"]["content"][0]["text"]


if __name__ == "__main__":
    # First live Bedrock call. Needs AWS creds + Bedrock access.
    #   python -m app.core.bedrock   (run from backend/)
    vector = embed_text("We agreed to launch on the 15th of March.")
    print(f"✅ Bedrock Titan responded. embedding dim = {len(vector)}")
    print(f"   first 5 values: {vector[:5]}")
