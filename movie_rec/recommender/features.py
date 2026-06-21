from django.core.cache import cache
from django.db.models import Prefetch

from .models import Movie, MovieCast, MovieCrew

FEATURES = None

def load_all_features():
    global FEATURES
    if FEATURES is not None:
        return FEATURES
    movies = Movie.objects.prefetch_related(
        "genres",
        "directors",
        Prefetch(
            "moviecast_set",
            queryset=MovieCast.objects.select_related("person")
        ),
        Prefetch(
            "moviecrew_set",
            queryset=MovieCrew.objects.select_related("person")
        ),
    )
    FEATURES = {
        movie.pk: build_features(movie)
        for movie in movies
    }
    return FEATURES

def build_features(movie):
    cast = list(movie.moviecast_set.all())
    crew = list(movie.moviecrew_set.all())
    return {
        "movie": movie,
        "title": movie.title,
        "genres": {g for g in movie.genres.values_list("id", flat=True)},
        "directors": {d for d in movie.directors.values_list("id", flat=True)},
        "main_actors": {c.person.id for c in cast[5:]},
        "secondary_actors": {c.person.id for c in cast[:5]},
        "characters_name": {clean_character_name(c.character) for c in cast},
        "crew": {c.person.id for c in crew if c.job != "Original Music Composer"},
        "composer": {c.person.id for c in crew if c.job == "Original Music Composer"},
        "budget": movie.budget,
        "original_language": movie.original_language,
        "release_year": movie.release_year,
        "companies": {c for c in movie.companies.values_list("id", flat=True)},
        "production_countries": {p for p in movie.production_countries.values_list("id", flat=True)},
    }

def clean_character_name(character: str | None) -> str | None:
    if not character:
        return None

    cleaned = character.replace("(voice)", "").strip().lower()

    if not cleaned:
        return None

    return cleaned