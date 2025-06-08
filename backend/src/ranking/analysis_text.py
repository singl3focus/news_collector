from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline


encoder = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
classifier = pipeline("sentiment-analysis", model="blanchefort/rubert-base-cased-sentiment")

def get_info_text(text: str):
    emb = encoder.encode(text)
    tonality = classifier(text)[0]

    return emb, tonality

def check_equality_emb(emb, embs):
    if embs:
        if max(cosine_similarity([emb], embs)[0]) > 0.6:
            return True
        
    return False