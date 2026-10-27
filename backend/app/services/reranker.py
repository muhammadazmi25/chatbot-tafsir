"""Cross-Encoder / FlagReranker — auto-detects model type.

- BAAI/bge-reranker-* → uses FlagEmbedding.FlagReranker (multilingual, Arabic/Indonesian support)
- Other models       → falls back to sentence_transformers.CrossEncoder (English-optimized)
"""

from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger('services.reranker')

_reranker_model = None


def _get_reranker():
    global _reranker_model
    if _reranker_model is None and settings.ENABLE_RERANKER:
        try:
            model_name = settings.RERANKER_MODEL
            if 'bge-reranker' in model_name.lower():
                from FlagEmbedding import FlagReranker
                import torch
                use_fp16 = torch.cuda.is_available()
                _reranker_model = FlagReranker(model_name, use_fp16=use_fp16)
                logger.info(f"BGE FlagReranker loaded: {model_name} (fp16={use_fp16})")
            else:
                # Fallback: sentence_transformers CrossEncoder (English-centric)
                from sentence_transformers import CrossEncoder
                _reranker_model = CrossEncoder(model_name)
                logger.info(f"CrossEncoder loaded: {model_name}")
        except Exception as e:
            logger.warning(f"Reranker not available: {e}")
    return _reranker_model


def get_reranker():
    """Alias for pre-warming or retrieving reranker model."""
    return _get_reranker()


def rerank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = None,
) -> List[Dict[str, Any]]:
    top_k = top_k or settings.RERANKER_TOP_K

    # Jika berjalan di CPU tanpa GPU CUDA, cross-encoder 560M param memakan waktu 4-5 menit.
    # Hybrid search (BGE-M3 dense + BM25 + RRF) sudah sangat presisi (<3 detik).
    # Reranker hanya dijalankan jika akselerasi GPU (CUDA) tersedia.
    import torch
    if not torch.cuda.is_available():
        logger.info("CUDA tidak tersedia (CPU mode): melewati heavy cross-encoder reranker (latensi < 3s)")
        return documents[:top_k]

    model = _get_reranker()

    if not model or not documents:
        return documents[:top_k]

    # Batasi kandidat reranker: di CPU batasi ke 8 kandidat (256 char) agar selesai < 1.5 detik
    import torch
    is_cpu = not torch.cuda.is_available()
    max_cands = 8 if is_cpu else 20
    max_chars = 256 if is_cpu else 512
    candidates = documents[:max_cands]

    try:
        pairs = [(query, doc.get('text', '')[:max_chars]) for doc in candidates]
        model_name = settings.RERANKER_MODEL.lower()

        if 'bge-reranker' in model_name:
            # FlagReranker.compute_score expects list of [query, passage] pairs
            scores = model.compute_score(pairs, normalize=True)
        else:
            scores = model.predict(pairs)

        # Handle both scalar and list returns
        if not hasattr(scores, '__iter__'):
            scores = [scores]

        for doc, score in zip(candidates, scores):
            doc['reranker_score'] = float(score)

        reranked = sorted(candidates, key=lambda x: x.get('reranker_score', 0), reverse=True)
        logger.info(f"Reranker ({settings.RERANKER_MODEL}): {len(candidates)} candidates → top {top_k}")
        return reranked[:top_k]

    except Exception as e:
        logger.error(f"Reranker error: {e}")
        return documents[:top_k]
