import time
from collections import defaultdict

from .models import Movie

# Global in-memory store of the table to cut down recommend time
_data = None


def clean_character_name(character: str | None) -> str | None:
    if not character:
        return None

    cleaned = character.replace("(voice)", "").strip().lower()

    if not cleaned:
        return None

    return cleaned


def get_character_ids(movie: Movie) -> set[int]:
    return {character.id for character in movie.characters.all()}


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


def load_data() -> dict[int, tuple[int | None, set[int], set[int]]]:
    # Build the global store once.
    global _data
    if _data is not None:
        return _data

    start = time.time()

    character_ids = defaultdict(set)
    for movie_id, character_id in Movie.characters.through.objects.values_list("movie_id", "character_id"):
        character_ids[movie_id].add(character_id)

    genre_ids = defaultdict(set)
    for movie_id, genre_id in Movie.genres.through.objects.values_list("movie_id", "genre_id"):
        genre_ids[movie_id].add(genre_id)

    _data = {
        movie_id: (parse_release_year(year), character_ids.get(movie_id, set()), genre_ids.get(movie_id, set()))
        for movie_id, year in Movie.objects.values_list("movielens_id", "release_year")
    }

    print(f"Loaded {len(_data)} movies into _data in {time.time() - start:.2f} seconds")
    return _data


def recommend(movie_id: int, top_n: int = 5) -> list[Movie]:
    start = time.time()
    data = load_data()

    if movie_id not in data:
        return []

    target_year, target_characters, target_genre_ids = data[movie_id]

    scored_movies = []

    for candidate_id, (candidate_year, candidate_characters, candidate_genre_ids) in data.items():
        if candidate_id == movie_id:
            continue

        char_overlap = len(target_characters & candidate_characters)
        year_score = calculate_year_score(target_year, candidate_year)
        genre_score = calculate_genre_score(target_genre_ids, candidate_genre_ids)

        total_score = 3.0 * char_overlap + 2.0 * year_score + 1.0 * genre_score

        if total_score > 0:
            scored_movies.append((total_score, candidate_id))

    scored_movies.sort(key=lambda item: item[0], reverse=True)
    top_ids = [candidate_id for _, candidate_id in scored_movies[:top_n]]

    movies_by_id = Movie.objects.in_bulk(top_ids)
    recommended_movies = [movies_by_id[movieid] for movieid in top_ids if movieid in movies_by_id]

    print(f"Recommend Elapsed: {time.time() - start:.2f} seconds")
    return recommended_movies
