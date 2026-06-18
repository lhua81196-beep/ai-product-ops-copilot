import json, os, numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class EnterpriseKnowledgeBase:
    def __init__(self, json_path=None):
        self.topics = []
        self.contents = []
        self.vectorizer = None
        self.matrix = None
        self.ready = False
        self.size = 0
        if json_path and os.path.exists(json_path):
            self.load_from_json(json_path)

    def load_from_json(self, json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.topics = [item["topic"] for item in data]
        self.contents = [item["content"] for item in data]
        self.size = len(self.topics)
        if not self.contents:
            self.ready = False
            return
        try:
            self.vectorizer = TfidfVectorizer()
            self.matrix = self.vectorizer.fit_transform(self.contents)
            self.ready = True
        except Exception:
            self.vectorizer = None
            self.matrix = None
            self.ready = False

    def search(self, query, top_k=3):
        if not self.ready or not query.strip():
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.matrix)[0]
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for i in top_idx:
            results.append({
                "topic": self.topics[i],
                "content": self.contents[i],
                "score": float(scores[i])
            })
        return results
