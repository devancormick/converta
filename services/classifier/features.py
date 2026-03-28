from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion, Pipeline

try:
    import textstat
    _TEXTSTAT = True
except ImportError:
    _TEXTSTAT = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
except ImportError:
    _VADER = None

try:
    from sentence_transformers import SentenceTransformer
    _SBERT = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    _SBERT = None

URGENCY_KEYWORDS = ["urgent", "limited time", "act now", "today only", "expires", "deadline", "hurry"]
CTA_KEYWORDS = ["apply now", "click here", "get started", "sign up", "learn more", "call now"]


class ReadabilityFeatures(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for text in X:
            words = text.split()
            sentences = re.split(r"[.!?]+", text)
            sentences = [s for s in sentences if s.strip()]
            word_count = len(words)
            char_count = len(text)
            sentence_count = max(len(sentences), 1)

            fk = textstat.flesch_kincaid_grade(text) if _TEXTSTAT else 0.0
            gf = textstat.gunning_fog(text) if _TEXTSTAT else 0.0
            sentiment = _VADER.polarity_scores(text)["compound"] if _VADER else 0.0
            urgency = sum(1 for kw in URGENCY_KEYWORDS if kw in text.lower())
            cta = sum(1 for kw in CTA_KEYWORDS if kw in text.lower())

            rows.append([
                word_count,
                char_count,
                sentence_count,
                word_count / sentence_count,
                fk,
                gf,
                sentiment,
                float(urgency),
                float(cta),
            ])
        return np.array(rows, dtype=float)


class SBertFeatures(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if _SBERT is None:
            return np.zeros((len(X), 384))
        return _SBERT.encode(list(X), show_progress_bar=False, batch_size=32)


def build_feature_pipeline() -> Pipeline:
    tfidf = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)
    union = FeatureUnion([
        ("tfidf", tfidf),
        ("readability", ReadabilityFeatures()),
        ("sbert", SBertFeatures()),
    ])
    return Pipeline([("features", union)])


def extract_features(texts: list[str], pipeline: Pipeline | None = None):
    if pipeline is None:
        pipeline = build_feature_pipeline()
    return pipeline.fit_transform(texts)
