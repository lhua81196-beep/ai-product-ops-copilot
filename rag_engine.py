import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader


# ======================
# 1. PDF读取（稳定增强版）
# ======================
def load_pdf(file):
    """
    支持 Streamlit uploaded_file
    """
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


# ======================
# 2. 文本切分（防空 + 稳定）
# ======================
def split_text(text, chunk_size=500):
    if not text or len(text.strip()) == 0:
        return []

    # 更稳的切分方式
    sentences = re.split(r'(?<=[。.!?])\s*', text)

    chunks = []
    chunk = ""

    for s in sentences:
        if not s:
            continue

        if len(chunk) + len(s) < chunk_size:
            chunk += s
        else:
            if chunk:
                chunks.append(chunk)
            chunk = s

    if chunk:
        chunks.append(chunk)

    # 🔥 防止极端情况：返回整段
    if len(chunks) == 0 and len(text) > 0:
        chunks = [text[:chunk_size]]

    return chunks


# ======================
# 3. VectorStore（稳定版）
# ======================
class VectorStore:
    def __init__(self, chunks):
        if not chunks:
            raise ValueError("chunks为空，无法构建知识库")

        self.chunks = chunks
        self.vectorizer = TfidfVectorizer()

        try:
            self.vectors = self.vectorizer.fit_transform(chunks)
        except:
            # fallback：防止TF-IDF崩
            self.vectors = None

    def search(self, query, top_k=3):
        if not query:
            return []

        # 如果TF-IDF失败，直接返回前几个chunk
        if self.vectors is None:
            return [
                {"text": c, "score": 0.0}
                for c in self.chunks[:top_k]
            ]

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors)[0]

        top_idx = scores.argsort()[-top_k:][::-1]

        results = []
        for i in top_idx:
            results.append({
                "text": self.chunks[i],
                "score": float(scores[i])
            })

        # 🔥 防止空返回
        if len(results) == 0:
            return [{"text": self.chunks[0], "score": 0.0}]

        return results


# ======================
# 4. 构建知识库入口（核心修复）
# ======================
def build_knowledge_base(pdf_text):
    if not pdf_text or len(pdf_text.strip()) == 0:
        raise ValueError("PDF解析失败：没有文本内容")

    chunks = split_text(pdf_text)

    if len(chunks) == 0:
        raise ValueError("chunk失败：没有生成内容")

    print("✅ PDF length:", len(pdf_text))
    print("✅ chunks:", len(chunks))

    return VectorStore(chunks)
