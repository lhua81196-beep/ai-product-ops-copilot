# -*- coding: utf-8 -*-
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def split_text(text, chunk_size=500):
    if not text:
        return []
    sentences = re.split(r'(?<=[。.!?])\s*', text)
    chunks, buf = [], ''
    for s in sentences:
        if len(buf) + len(s) < chunk_size:
            buf += s
        else:
            if buf:
                chunks.append(buf)
            buf = s
    if buf:
        chunks.append(buf)
    return chunks if chunks else [text[:chunk_size]]


class VectorStore:
    def __init__(self, chunks=None, metadata=None):
        self.chunks = chunks if chunks else []
        self.metadata = metadata or [{} for _ in self.chunks]
        if not self.chunks:
            self.vectorizer = None
            self.vectors = None
            return
        try:
            self.vectorizer = TfidfVectorizer()
            self.vectors = self.vectorizer.fit_transform(self.chunks)
        except Exception:
            self.vectorizer = None
            self.vectors = None

    def search(self, query, top_k=3):
        if not self.chunks:
            return []
        if self.vectors is None:
            return [{'content': c, 'meta': self.metadata[i], 'score': 0.0}
                    for i, c in enumerate(self.chunks[:top_k])]
        try:
            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.vectors)[0]
            top_idx = scores.argsort()[-top_k:][::-1]
            results = []
            for i in top_idx:
                meta = self.metadata[i] if i < len(self.metadata) else {}
                results.append({'content': self.chunks[i], 'meta': meta, 'score': float(scores[i])})
            return results
        except Exception:
            return [{'content': self.chunks[0], 'meta': {}, 'score': 0.0}] if self.chunks else []


def build_knowledge_base(pdf_text, source='unknown'):
    chunks = split_text(pdf_text)
    metadata = [{'source': source, 'chunk_id': i} for i in range(len(chunks))]
    return VectorStore(chunks, metadata)
