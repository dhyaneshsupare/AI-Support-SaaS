from concurrent.futures import ThreadPoolExecutor

import numpy as np
from huggingface_hub import InferenceClient
from langchain_core.embeddings import Embeddings

from app.config import get_settings


class ConfigError(RuntimeError):
    pass


class HFInferenceEmbeddings(Embeddings):
    """Embeddings via the Hugging Face Inference API (one request per text, run in parallel)."""

    def __init__(self, model: str, token: str):
        if not token:
            raise ConfigError("HF_TOKEN is not set")
        self.client = InferenceClient(model=model, token=token)

    def _embed(self, text: str) -> list[float]:
        vec = np.asarray(self.client.feature_extraction(text), dtype=float)
        while vec.ndim > 1:  # token-level output -> mean-pool to one sentence vector
            vec = vec.mean(axis=0)
        norm = np.linalg.norm(vec)
        return (vec / norm if norm else vec).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        with ThreadPoolExecutor(max_workers=8) as pool:
            return list(pool.map(self._embed, texts))

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embeddings() -> Embeddings:
    s = get_settings()
    return HFInferenceEmbeddings(model=s.embedding_model, token=s.hf_token)
