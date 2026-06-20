from .models import Movie


def recommend(movie_id: int, top_n: int = 5) -> list[Movie]:
    import numpy as np

    target_movie = Movie.objects.get(pk=movie_id)
    target_vector = target_movie.get_overview_vector()

    if target_vector is None:
        return []

    target_norm = np.linalg.norm(target_vector)
    if target_norm == 0:
        return []

    candidates = Movie.objects.exclude(pk=movie_id).exclude(overview_vector__isnull=True)

    scored_movies = []

    for candidate in candidates:
        candidate_vector = candidate.get_overview_vector()

        if candidate_vector is None:
            continue

        candidate_norm = np.linalg.norm(candidate_vector)
        if candidate_norm == 0:
            continue

        similarity = float(
            np.dot(target_vector, candidate_vector) / (target_norm * candidate_norm)
        )

        scored_movies.append({"movie": candidate, "score": similarity})

    scored_movies.sort(key=lambda item: item["score"], reverse=True)
    top_recommendations = scored_movies[:top_n]
    recommended_movies = [item["movie"] for item in top_recommendations]

    return recommended_movies
