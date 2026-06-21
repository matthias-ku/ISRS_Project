from .features import load_all_features
from .models import Movie

def calculate_budget_score(budget_a:int, budget_b:int)->int:
    diff = abs(budget_a-budget_b)
    return 100-round((diff/budget_a)*100)

def recommend_budget(movie_id: int, top_n: int = 5) -> list[Movie]:
    features = load_all_features()
    target_data = features[movie_id]
    target_budget = target_data["budget"]
    target_genre_ids = target_data["genres"]
    target_language = target_data["original_language"]
    target_companies = target_data["companies"]
    target_countries = target_data["production_countries"]

    candidate_features = [features[f] for f in features if f != movie_id]

    scored_movies = []
    for candidate in candidate_features:
        candidate_budget = candidate["budget"]
        candidate_genre_ids = candidate['genres']
        candidate_language = candidate["original_language"]
        candidate_companies = candidate["companies"]
        candidate_countries = candidate["production_countries"]
        budget_score = 0
        language_score = 0
        if target_budget and candidate_budget:
            budget_score = calculate_budget_score(target_budget,candidate_budget)
        if candidate_language and target_language:
            if candidate_language==target_language:
                language_score += 15.0
        companies_score = len(target_companies & candidate_companies)
        countries_score = len(target_countries & candidate_countries)
        genre_score = len(target_genre_ids & candidate_genre_ids)
        total_score = budget_score + language_score + genre_score + companies_score * 30.0 + countries_score * 15.0
        if total_score > 0:
            scored_movies.append(
                {
                    "movie": candidate["movie"],
                    "score": total_score,
                    "budget_similarity": budget_score,
                    "language": target_language==candidate_language,
                    "genre_score": genre_score,
                    "companies_score": companies_score,
                    "countries_score": countries_score,
                }
            )

    scored_movies.sort(key=lambda item: item["score"], reverse=True)
    top_recommendations = scored_movies[:top_n]
    ids = [item["movie"] for item in top_recommendations]
    movies = Movie.objects.in_bulk(ids)
    recommended_movies = [movies[i] for i in ids]
    return recommended_movies