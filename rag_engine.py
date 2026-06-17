import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader


# ======================
# 1. PDF读取
# ======================
def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text


# ======================
# 2. 切分文本
# ======================
def split_text(text, chunk_size=500):
    sentences = re.split(r'(?<=[。.!?])\s*', text)
    chunks = []
    chunk = ""

    for s in sentences:
        if len(chunk) + len(s) < chunk_size:
            chunk += s
        else:
            chunks.append(chunk)
            chunk = s

    if chunk:
        chunks.append(chunk)

    return chunks


# ======================
# 3. 轻量VectorStore（TF-IDF）
# ======================
class VectorStore:
    def __init__(self, chunks):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer()
        self.vectors = self.vectorizer.fit_transform(chunks)

    def search(self, query, top_k=3):
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors)[0]

        top_idx = scores.argsort()[-top_k:][::-1]

        return [
            {
                "text": self.chunks[i],
                "score": float(scores[i])
            }
            for i in top_idx if scores[i] > 0
        ]


# ======================
# 4. 文本处理入口
# ======================
def build_knowledge_base(pdf_text):
    chunks = split_text(pdf_text)
    print("chunks:", len(chunks))
    return VectorStore(chunks)
