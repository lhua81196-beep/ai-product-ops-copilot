import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader


# =========================
# 1. PDF读取（稳定版）
# =========================
def load_pdf(file):
    """支持 Streamlit 上传文件 / 本地文件"""
    reader = PdfReader(file)
    text = ""

    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        except:
            continue

    return text.strip()


# =========================
# 2. 文本切分（防空优化）
# =========================
def split_text(text, chunk_size=500):
    if not text:
        return []

    sentences = re.split(r'(?<=[。.!?])\s*', text)

    chunks = []
    buf = ""

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


# =========================
# 3. 向量检索（TF-IDF轻量版）
# =========================
class VectorStore:
    def __init__(self, chunks):
        self.chunks = chunks or []

        if not self.chunks:
            self.vectorizer = None
            self.vectors = None
            return

        try:
            self.vectorizer = TfidfVectorizer()
            self.vectors = self.vectorizer.fit_transform(self.chunks)
        except:
            self.vectorizer = None
            self.vectors = None

    def search(self, query, top_k=3):
        """稳定检索：永远返回top_k（即使低质量）"""

        if not self.chunks:
            return []

        # fallback：无向量器
        if self.vectorizer is None:
            return [
                {"text": c, "score": 0.0}
                for c in self.chunks[:top_k]
            ]

        try:
            q_vec = self.vectorizer.transform([query])
            scores = cosine_similarity(q_vec, self.vectors)[0]

            top_idx = scores.argsort()[-top_k:][::-1]

            results = []
            for i in top_idx:
                results.append({
                    "text": self.chunks[i],
                    "score": float(scores[i])
                })

            return results

        except:
            return [
                {"text": self.chunks[0], "score": 0.0}
            ]


# =========================
# 4. 构建知识库入口
# =========================
def build_knowledge_base(pdf_text):
    chunks = split_text(pdf_text)
    return VectorStore(chunks)
