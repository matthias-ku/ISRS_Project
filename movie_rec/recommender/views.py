from django.shortcuts import redirect, render, get_object_or_404

from .models import Movie
from .recommender_characters import recommend


def index(request):
    error = None
    if request.method == "POST":
        query = request.POST.get("query", "").strip()
        if not query:
            error = "Please enter a movie ID or title."
        elif query.isdigit():
            movie_id = int(query)
            if Movie.objects.filter(pk=movie_id).exists():
                return redirect("movie-detail", pk=movie_id)
            error = f"No movie found with ID {movie_id}."
        else:
            # Title search: pick the best match by rating/popularity.
            match = (
                Movie.objects.filter(title__icontains=query)
                .order_by("-num_ratings", "-avg_rating")
                .first()
            )
            if match:
                return redirect("movie-detail", pk=match.movielens_id)
            error = f"No movie found matching '{query}'."
    return render(request, "recommender/index.html", {"error": error})


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.prefetch_related(
            "genres",
            "keywords",
            "directors",
            "moviecast_set__person",
            "moviecrew_set__person",
        ),
        pk=pk,
    )
    debug_print_movie(movie)
    recommendations = recommend(movie.movielens_id, top_n=5)
    return render(request, "recommender/recommendations.html", {
        "movie": movie,
        "recommendations": recommendations,
    })


def debug_print_movie(movie):
    # print all info for debugging
    print("------------------------------------------------------------")
    print(f"MOVIE {movie.movielens_id}: {movie.title}")
    print("------------------------------------------------------------")

    for field in movie._meta.fields:
        if field.name == "overview_vector":
            continue
        print(f"{field.name}: {getattr(movie, field.attname)}")

    print(f"genres: {[g.name for g in movie.genres.all()]}")
    print(f"keywords: {[k.name for k in movie.keywords.all()]}")
    print(f"directors: {[d.name for d in movie.directors.all()]}")

    print("cast:")
    for mc in movie.moviecast_set.all():
        print(f"[{mc.order}] {mc.person.name} as {mc.character}")

    print("crew:")
    for mc in movie.moviecrew_set.all():
        print(f"{mc.department} / {mc.job}: {mc.person.name}")

    print("------------------------------------------------------------")
