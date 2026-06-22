from pyexpat import features

from .features import load_all_features
from .models import Movie
import time
import numpy as np

def recommend(movie_id: int, top_n: int = 5) -> list[Movie]:
    start = time.time()
    features = load_all_features()

    #target_movie = Movie.objects.get(pk=movie_id)
    #target_vector = target_movie.get_overview_vector()
    target_movie = features[movie_id]
    target_vector = target_movie["overview"]

    if target_vector is None:
        return []

    target_norm = np.linalg.norm(target_vector)
    if target_norm == 0:
        return []

    #candidates = Movie.objects.exclude(pk=movie_id).exclude(overview_vector__isnull=True)
    candidates = [features[f] for f in features if (f!=movie_id and not features[f]["overview"] is None) ]
    scored_movies = []

    for candidate in candidates:
        #candidate_vector = candidate.get_overview_vector()
        candidate_vector = candidate["overview"]

        if candidate_vector is None:
            continue

        candidate_norm = np.linalg.norm(candidate_vector)
        if candidate_norm == 0:
            continue

        similarity = float(
            np.dot(target_vector, candidate_vector) / (target_norm * candidate_norm)
        )

        scored_movies.append({"movie": candidate["movie"], "score": similarity})

    scored_movies.sort(key=lambda item: item["score"], reverse=True)
    top_recommendations = scored_movies[:top_n]
    ids = [item["movie"] for item in top_recommendations]
    movies = Movie.objects.in_bulk(ids)
    recommended_movies = [movies[i] for i in ids]
    print(f"Recommend Story Elapsed: {time.time() - start:.2f} seconds")
    return recommended_movies
