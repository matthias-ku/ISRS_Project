import time
import numpy as np
from .features import load_all_features
from .models import Movie

_cache = None

def _build_cache(features):
    global _cache
    if _cache is not None:
        return _cache

    movie_ids = list(features.keys())
    n = len(movie_ids)
    id_to_index = {mid: i for i, mid in enumerate(movie_ids)}

    from scipy.sparse import csr_matrix

    # --- Keyword binary matrix ---
    all_keywords = set()
    for mid in movie_ids:
        all_keywords.update(features[mid].get("keywords") or [])
    kw_list = list(all_keywords)
    kw_index = {k: i for i, k in enumerate(kw_list)}

    kw_rows, kw_cols = [], []
    for i, mid in enumerate(movie_ids):
        for kw in (features[mid].get("keywords") or []):
            if kw in kw_index:
                kw_rows.append(i)
                kw_cols.append(kw_index[kw])
    kw_matrix = csr_matrix(
        (np.ones(len(kw_rows)), (kw_rows, kw_cols)),
        shape=(n, len(kw_list))
    )

    # --- Genre binary matrix ---
    all_genres = set()
    for mid in movie_ids:
        all_genres.update(features[mid].get("genres") or [])
    genre_list = list(all_genres)
    genre_index = {g: i for i, g in enumerate(genre_list)}

    g_rows, g_cols = [], []
    for i, mid in enumerate(movie_ids):
        for g in (features[mid].get("genres") or []):
            if g in genre_index:
                g_rows.append(i)
                g_cols.append(genre_index[g])
    genre_matrix = csr_matrix(
        (np.ones(len(g_rows)), (g_rows, g_cols)),
        shape=(n, len(genre_list))
    )

    kw_counts = np.asarray(kw_matrix.sum(axis=1)).flatten()
    genre_counts = np.asarray(genre_matrix.sum(axis=1)).flatten()

    # --- Overview embedding matrix (same as story recommender) ---
    overview_vectors = []
    for mid in movie_ids:
        v = features[mid].get("overview")
        if v is not None and np.linalg.norm(v) > 0:
            overview_vectors.append(v / np.linalg.norm(v))  # pre-normalize
        else:
            overview_vectors.append(np.zeros_like(overview_vectors[0]) if overview_vectors else None)

    # handle case where first movies have no vector
    vec_dim = next((v for v in overview_vectors if v is not None), None)
    if vec_dim is not None:
        overview_matrix = np.array([
            v if v is not None else np.zeros(len(vec_dim))
            for v in overview_vectors
        ])  # shape (n, embedding_dim)
    else:
        overview_matrix = None

    _cache = {
        "movie_ids": movie_ids,
        "id_to_index": id_to_index,
        "kw_matrix": kw_matrix,
        "kw_counts": kw_counts,
        "genre_matrix": genre_matrix,
        "genre_counts": genre_counts,
        "overview_matrix": overview_matrix,
    }
    return _cache


def _jaccard_row_vs_all(binary_matrix, counts, target_idx):
    target_row = binary_matrix[target_idx]  # sparse (1, m)
    # .toarray() converts sparse result to dense before flattening
    intersection = np.asarray(binary_matrix.dot(target_row.T).toarray()).flatten().astype(float)
    target_count = float(counts[target_idx])
    union = counts + target_count - intersection
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(union > 0, intersection / union, 0.0)


def recommend_keywords(movie_id: int, top_n: int = 5) -> list[Movie]:
    start = time.time()

    features = load_all_features()
    cache = _build_cache(features)

    if movie_id not in cache["id_to_index"]:
        return []

    idx = cache["id_to_index"][movie_id]
    movie_ids = cache["movie_ids"]

    kw_scores = _jaccard_row_vs_all(cache["kw_matrix"], cache["kw_counts"], idx)
    genre_scores = _jaccard_row_vs_all(cache["genre_matrix"], cache["genre_counts"], idx)

    # reuse the precomputed embedding — same as story recommender, no TF-IDF needed
    if cache["overview_matrix"] is not None:
        overview_scores = cache["overview_matrix"] @ cache["overview_matrix"][idx]  # (n,)
    else:
        overview_scores = np.zeros(len(movie_ids))

    target_kw_count = cache["kw_counts"][idx]

    if target_kw_count >= 3:
        total_scores = 0.7 * kw_scores + 0.2 * genre_scores + 0.1 * overview_scores
    elif target_kw_count > 0:
        total_scores = 0.4 * kw_scores + 0.3 * genre_scores + 0.3 * overview_scores
    else:
        total_scores = 0.4 * genre_scores + 0.6 * overview_scores

    total_scores[idx] = 0.0

    top_indices = np.argpartition(total_scores, -top_n)[-top_n:]
    top_indices = top_indices[np.argsort(total_scores[top_indices])[::-1]]
    top_ids = [movie_ids[i] for i in top_indices if total_scores[i] > 0]

    movies_by_id = Movie.objects.in_bulk(top_ids)
    recommended_movies = [movies_by_id[mid] for mid in top_ids if mid in movies_by_id]

    print(f"Recommend Keywords Elapsed: {time.time() - start:.2f} seconds")
    return recommended_movies