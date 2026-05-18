from django.shortcuts import redirect, render, get_object_or_404

from .models import Movie
from .recommender_characters import recommend


def index(request):
    error = None
    if request.method == "POST":
        raw = request.POST.get("movie_id", "").strip()
        if raw.isdigit():
            movie_id = int(raw)
            if Movie.objects.filter(pk=movie_id).exists():
                return redirect("movie-detail", pk=movie_id)
            error = f"No movie found with ID {movie_id}."
        else:
            error = "Please enter a valid numeric ID."
    return render(request, "recommender/index.html", {"error": error})


def movie_detail(request, pk):
    movie = get_object_or_404(
        Movie.objects.prefetch_related(
            "genres", "keywords", "directors", "moviecast_set__person"
        ),
        pk=pk,
    )
    recommendations = recommend(movie.movielens_id, top_n=5)
    return render(request, "recommender/recommendations.html", {
        "movie": movie,
        "recommendations": recommendations,
    })
