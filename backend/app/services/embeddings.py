from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Modelo liviano y gratuito — no necesita API key
model = SentenceTransformer("all-MiniLM-L6-v2")

def generate_embedding(text: str) -> List[float]:
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()

def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    a = np.array(vec1)
    b = np.array(vec2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))