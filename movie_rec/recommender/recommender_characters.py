from .models import Movie


def clean_character_name(character: str | None) -> str | None:
    if not character:
        return None

    cleaned = character.replace("(voice)", "").strip().lower()

    if not cleaned:
        return None

    return cleaned


def get_character_names(movie: Movie) -> set[str]:
    characters = set()

    for cast_member in movie.moviecast_set.all():
        character = clean_character_name(cast_member.character)

        if character:
            characters.add(character)

    return characters


def get_genre_ids(movie: Movie) -> set[int]:
    return {genre.id for genre in movie.genres.all()}


def parse_release_year(release_year: str | None) -> int | None:
    if release_year and release_year.isdigit():
        return int(release_year)

    return None


def calculate_year_score(year_a: int | None, year_b: int | None) -> float:
    if year_a is None or year_b is None:
        return 0.0

    return 1.0 / (1.0 + abs(year_a - year_b))


def calculate_genre_score(genre_ids_a: set[int], genre_ids_b: set[int]) -> float:
    genre_union = genre_ids_a | genre_ids_b

    if not genre_union:
        return 0.0

    shared_genres = genre_ids_a & genre_ids_b
    return len(shared_genres) / len(genre_union)


def recommend(movie_id: int, top_n: int = 5) -> list[Movie]:
    target_movie = Movie.objects.prefetch_related("genres", "moviecast_set").get(pk=movie_id)

    target_characters = get_character_names(target_movie)
    target_genre_ids = get_genre_ids(target_movie)
    target_year = parse_release_year(target_movie.release_year)

    candidates = Movie.objects.exclude(pk=movie_id).prefetch_related("genres", "moviecast_set")

    scored_movies = []

    for candidate in candidates:
        candidate_characters = get_character_names(candidate)
        candidate_genre_ids = get_genre_ids(candidate)
        candidate_year = parse_release_year(candidate.release_year)

        char_overlap = len(target_characters & candidate_characters)
        year_score = calculate_year_score(target_year, candidate_year)
        genre_score = calculate_genre_score(target_genre_ids, candidate_genre_ids)

        total_score = 3.0 * char_overlap + 2.0 * year_score + 1.0 * genre_score

        if total_score > 0:
            scored_movies.append(
                {
                    "movie": candidate,
                    "score": total_score,
                    "char_overlap": char_overlap,
                    "year_score": year_score,
                    "genre_score": genre_score,
                }
            )

    scored_movies.sort(key=lambda item: item["score"], reverse=True)
    top_recommendations = scored_movies[:top_n]
    recommended_movies = [item["movie"] for item in top_recommendations]

    return recommended_movies
