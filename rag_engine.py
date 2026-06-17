# -*- coding: utf-8 -*-

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader
import re


# =========================
# 1. PDF 稳定解析
# =========================

def load_pdf_text(file) -> str:
    """
    稳定PDF解析（替代 PyPDF2）
    """
    reader = PdfReader(file)
    text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text)

    return "\n".join(text)


# =========================
# 2. 文本清洗（关键增强）
# =========================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9.,;:!?()（） ]", "", text)

    return text.strip()


# =========================
# 3. 稳定切分（防空chunk）
# =========================

def split_text(text, chunk_size=400, overlap=80):
    text = clean_text(text)

    if len(text) < 50:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        chunk = chunk.strip()

        # ❗过滤空chunk
        if len(chunk) > 30:
            chunks.append(chunk)

        start = end - overlap

    return chunks


# =========================
# 4. 稳定RAG向量库
# =========================

class VectorStore:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words=None  # 避免中文误伤
        )
        self.texts = []
        self.matrix = None

    def add(self, texts, metadata=None):
        """
        texts: list[str]
        metadata: list[dict]
        """
        if not texts:
            return

        if metadata is None:
            metadata = [{} for _ in texts]

        # 合并数据
        self.texts.extend([(t, m) for t, m in zip(texts, metadata)])

        all_texts = [t for t, _ in self.texts]

        # ❗防空保护
        all_texts = [t for t in all_texts if len(t.strip()) > 20]

        if len(all_texts) == 0:
            return

        self.matrix = self.vectorizer.fit_transform(all_texts)

    def search(self, query, top_k=3):
        """
        稳定检索 + fallback
        返回 list[dict]，每项：
          {"content": str, "meta": {"source": str, "chunk_id": int}, "score": float}
        """
        if self.matrix is None or len(self.texts) == 0:
            return []

        query = clean_text(query)

        if len(query) < 2:
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]

        top_idx = np.argsort(scores)[::-1][:top_k]

        results = []
        for i in top_idx:
            text, meta = self.texts[i]
            # 防御：meta 缺失时填充默认值
            if not isinstance(meta, dict):
                meta = {}
            meta.setdefault("source", "unknown")
            meta.setdefault("chunk_id", i)
            results.append({
                "content": text,
                "meta": meta,
                "score": float(scores[i])
            })

        return results
