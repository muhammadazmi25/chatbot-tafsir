"""Hybrid Search: BM25 + Semantic RRF fusion (reused from chatbot-unand, generic)."""

import re
from typing import List, Dict, Any
from collections import defaultdict
import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger('services.hybrid_search')

STOPWORDS = {
    # Indonesian
    'dan', 'yang', 'di', 'ke', 'dari', 'ini', 'itu', 'dengan', 'untuk',
    'pada', 'adalah', 'atau', 'dalam', 'oleh', 'sebagai', 'tidak', 'juga',
    'akan', 'sudah', 'telah', 'bisa', 'dapat', 'harus', 'serta', 'tersebut',
    'bahwa', 'seperti', 'lebih', 'antara', 'karena', 'setelah', 'semua',
    'ada', 'bagi', 'bila', 'saat', 'masih', 'hanya', 'sangat', 'secara',
    # English
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'to', 'of', 'in', 'for', 'on', 'with',
    'at', 'by', 'from', 'as', 'into', 'not', 'no', 'nor', 'so', 'than',
}


def tokenize(text: str) -> List[str]:
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def reciprocal_rank_fusion(
    result_lists: List[List[Dict[str, Any]]],
    weights: List[float] = None,
    k: int = None,
) -> List[Dict[str, Any]]:
    k = k or settings.RRF_K
    weights = weights or [1.0] * len(result_lists)
    total = sum(weights)
    weights = [w / total for w in weights]

    doc_scores: dict = defaultdict(float)
    doc_data: dict = {}

    for list_idx, result_list in enumerate(result_lists):
        w = weights[list_idx]
        for rank, doc in enumerate(result_list, 1):
            doc_id = f"{doc.get('source', '')}_{doc.get('text', '')[:100]}"
            doc_scores[doc_id] += w * (1.0 / (k + rank))
            if doc_id not in doc_data:
                doc_data[doc_id] = doc.copy()

    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for doc_id, rrf_score in sorted_docs:
        doc = doc_data[doc_id]
        doc['rrf_score'] = rrf_score
        results.append(doc)
    return results


class HybridSearchService:
    def __init__(self):
        self.bm25 = None
        self.corpus: List[Dict] = []

    def _build_index(self, documents: List[Dict]):
        self.corpus = documents
        tokenized = [tokenize(d.get('text', '')) for d in documents]
        self.bm25 = BM25Okapi(tokenized)

    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        if not self.bm25:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        top_idx = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_idx:
            if scores[idx] > 0:
                doc = self.corpus[idx].copy()
                doc['bm25_score'] = float(scores[idx])
                results.append(doc)
        return results

    def hybrid_search(
        self,
        query: str,
        semantic_results: List[Dict],
        top_k: int = None,
        semantic_weight: float = None,
        bm25_weight: float = None,
    ) -> List[Dict]:
        top_k = top_k or settings.INITIAL_RETRIEVAL_K
        sw = semantic_weight or settings.SEMANTIC_WEIGHT
        bw = bm25_weight or settings.BM25_WEIGHT

        # Build BM25 from semantic results as mini-corpus
        if semantic_results:
            self._build_index(semantic_results)

        bm25_results = self._bm25_search(query, top_k)
        if bm25_results:
            fused = reciprocal_rank_fusion(
                [semantic_results, bm25_results],
                weights=[sw, bw],
                k=settings.RRF_K,
            )
        else:
            fused = semantic_results

        logger.info(f"Hybrid: {len(semantic_results)} sem + {len(bm25_results)} bm25 → {len(fused)} fused")
        return fused[:top_k]


hybrid_search_service = HybridSearchService()
