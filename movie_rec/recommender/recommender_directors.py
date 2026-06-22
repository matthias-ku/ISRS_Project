import time

from .features import load_all_features
from .models import Movie

def recommend_dir(movie_id: int, top_n: int = 5) -> list[Movie]:
    start = time.time()
    features = load_all_features()
    target_data = features[movie_id]
    target_directors = target_data['directors']
    target_genre_ids = target_data['genres']
    target_main_actors = target_data['main_actors']
    target_secondary_actors = target_data["secondary_actors"]
    target_crew = target_data['crew']
    target_composer = target_data['composer']
    scored_movies = []
    candidate_features = [features[f] for f in features if f!=movie_id]
    for candidate in candidate_features:

        candidate_directors = candidate['directors']
        candidate_genre_ids = candidate['genres']
        candidate_main_actors = candidate['main_actors']
        candidate_secondary_actors = candidate["secondary_actors"]
        candidate_crew = candidate['crew']
        candidate_composer = candidate['composer']

        directors_overlap = len(target_directors & candidate_directors)
        main_actors_overlap = len(target_main_actors & candidate_main_actors)
        actors_overlap = len((target_secondary_actors&candidate_secondary_actors)|(target_main_actors&candidate_secondary_actors)|(candidate_main_actors&target_secondary_actors))
        genre_score = len(target_genre_ids & candidate_genre_ids)
        crew_overlap = len(target_crew & candidate_crew)
        composer_overlap = len(target_composer & candidate_composer)


        total_score = 100.0 * directors_overlap + 80.0 * main_actors_overlap+ 20.0 * actors_overlap + 30.0 * composer_overlap + 20.0 * crew_overlap + 5.0 * genre_score
        if total_score > 0:
            scored_movies.append({
                    "movie": candidate['movie'],
                    "score": total_score,
                    "directors_overlap": directors_overlap,
                    "main_actors_overlap": main_actors_overlap,
                    "actors_overlap": actors_overlap,
                    "crew_overlap": crew_overlap,
                    "composer_overlap": composer_overlap,
                    "genre_score": genre_score,
                })
    scored_movies.sort(key=lambda item: item["score"], reverse=True)
    top_recommendations = scored_movies[:top_n]
    ids = [item["movie"] for item in top_recommendations]
    movies = Movie.objects.in_bulk(ids)
    recommended_movies = [movies[i] for i in ids]
    print(f"Recommend Director Elapsed: {time.time() - start:.2f} seconds")
    return recommended_movies