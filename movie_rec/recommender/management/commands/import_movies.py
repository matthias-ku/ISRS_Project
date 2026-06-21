import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from recommender.models import Genre, Keyword, Movie, MovieCast, MovieCrew, Person, Company, Country


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--data-dir", default=None)
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--update-existing", action="store_true", default=False)

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        data_dir = options["data_dir"] or os.path.join(base_dir, "extracted_content_ml-latest")

        if not os.path.isdir(data_dir):
            self.stderr.write(f"Data directory not found: {data_dir}")
            return

        files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
        if options["limit"]:
            files = files[: options["limit"]]

        total = len(files)
        self.stdout.write(f"Found {total} JSON files")

        existing_ids = set(Movie.objects.values_list("movielens_id", flat=True))
        imported = 0
        skipped = 0
        errors = 0

        for i, filename in enumerate(files, 1):
            if i % 200 == 0 or i == total:
                self.stdout.write(f"{i}/{total}  imported={imported}  skipped={skipped}  errors={errors}")

            movielens_id = int(os.path.splitext(filename)[0])

            if not options["update_existing"] and movielens_id in existing_ids:
                skipped += 1
                continue

            try:
                with open(os.path.join(data_dir, filename), encoding="utf-8") as fh:
                    data = json.load(fh)
                with transaction.atomic():
                    import_movie(movielens_id, data)
                imported += 1
            except Exception as exc:
                self.stderr.write(f"Error importing {filename}: {exc}")
                errors += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. imported={imported}  skipped={skipped}  errors={errors}"))


def import_movie(movielens_id, data):
    ml = data.get("movielens") or {}
    tmdb = data.get("tmdb") or {}

    release_date = parse_date(ml.get("releaseDate") or tmdb.get("release_date"))

    movie, _ = Movie.objects.update_or_create(
        movielens_id=movielens_id,
        defaults=dict(
            tmdb_id=ml.get("tmdbMovieId") or tmdb.get("id"),
            imdb_id=ml.get("imdbMovieId") or (tmdb.get("imdb_id") or "").lstrip("tt") or None,
            title=ml.get("title") or tmdb.get("title") or "",
            original_title=ml.get("originalTitle") or tmdb.get("original_title"),
            release_year=ml.get("releaseYear") or (str(release_date.year) if release_date else None),
            release_date=release_date,
            runtime=ml.get("runtime") or tmdb.get("runtime"),
            overview=ml.get("plotSummary") or tmdb.get("overview"),
            tagline=tmdb.get("tagline") or None,
            poster_path=ml.get("posterPath") or tmdb.get("poster_path"),
            backdrop_path=tmdb.get("backdrop_path"),
            popularity=tmdb.get("popularity"),
            vote_average=tmdb.get("vote_average"),
            vote_count=tmdb.get("vote_count"),
            avg_rating=ml.get("avgRating"),
            num_ratings=ml.get("numRatings"),
            budget=tmdb.get("budget") or None,
            revenue=tmdb.get("revenue") or None,
            adult=tmdb.get("adult", False),
            original_language=tmdb.get("original_language"),
            status=tmdb.get("status"),
        ),
    )

    # Genres
    genre_names = ml.get("genres") or [g["name"] for g in tmdb.get("genres") or []]
    genres = [Genre.objects.get_or_create(name=name)[0] for name in genre_names if name]
    movie.genres.set(genres)

    # Keywords
    keywords = []
    for kw in tmdb.get("keywords") or []:
        keywords.append(get_or_create_keyword(kw))
    movie.keywords.set(keywords)

    # Directors
    tmdb_directors = [c for c in (tmdb.get("credits") or {}).get("crew") or [] if c.get("job") == "Director"]
    director_entries = tmdb_directors or [{"name": name, "id": None} for name in (ml.get("directors") or []) if name]
    movie.directors.set([get_or_create_person(entry) for entry in director_entries])

    # Cast
    MovieCast.objects.filter(movie=movie).delete()
    cast_entries = sorted((tmdb.get("credits") or {}).get("cast") or [], key=lambda c: c.get("order", 999))[:10]
    MovieCast.objects.bulk_create([
        MovieCast(movie=movie, person=get_or_create_person(entry), character=entry.get("character"), order=entry.get("order"))
        for entry in cast_entries
    ])

    # Companies
    companies_id = [c["id"] for c in tmdb.get("production_companies") or []]
    companies = [Company.objects.get_or_create(id_company=id)[0] for id in companies_id if id]
    movie.companies.set(companies)

    # Production countries
    countries_names = [c["name"] for c in tmdb.get("production_countries") or []]
    countries = [Country.objects.get_or_create(name=name)[0] for name in countries_names if name]
    movie.production_countries.set(countries)

    # Crew (directors, writers, production, music, etc.)
    MovieCrew.objects.filter(movie=movie).delete()
    crew_rows = []
    seen = set()
    for entry in (tmdb.get("credits") or {}).get("crew") or []:
        person = get_or_create_person(entry)
        key = (person.pk, entry.get("department"), entry.get("job"))
        if key in seen:
            continue
        seen.add(key)
        crew_rows.append(
            MovieCrew(movie=movie, person=person, department=entry.get("department"), job=entry.get("job"))
        )
    MovieCrew.objects.bulk_create(crew_rows)


def get_or_create_keyword(kw):
    # Both name and tmdb_id are unique, so match an existing row
    tmdb_id = kw.get("id")
    name = (kw.get("name") or "").strip()

    if tmdb_id:
        obj = Keyword.objects.filter(tmdb_id=tmdb_id).first()
        if obj:
            return obj

    obj = Keyword.objects.filter(name=name).first()
    if obj:
        return obj

    return Keyword.objects.create(name=name, tmdb_id=tmdb_id or None)


def get_or_create_person(entry):
    tmdb_id = entry.get("id")
    name = (entry.get("name") or "").strip()
    if tmdb_id:
        person, _ = Person.objects.get_or_create(tmdb_id=tmdb_id, defaults={"name": name, "profile_path": entry.get("profile_path")})
    else:
        person, _ = Person.objects.get_or_create(name=name, tmdb_id=None)
    return person


def parse_date(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None
