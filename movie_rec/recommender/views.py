from concurrent.futures import ThreadPoolExecutor

from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse

from .models import Movie
from .recommender_characters import recommend
from .recommender_directors import recommend_dir
from .recommender_budget import recommend_budget
from .recommender_keywords import recommend_keywords

from .recommender_story import recommend as recommend_story
from django.views.decorators.cache import cache_page

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


def movie_detail_character(request, pk):
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
    recommendations = recommend(movie.movielens_id, top_n=5)
    return render(request, "recommender/recommendations.html", {
        "movie": movie,
        "recommendations": recommendations,
    })


def movie_detail_story(request, pk):
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
    recommendations = recommend_story(movie.movielens_id, top_n=5)
    return render(request, "recommender/recommendations.html", {
        "movie": movie,
        "recommendations": recommendations,
    })


@cache_page(3600)
def movie_detail_async(request, pk):  # movie_detail_async
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
    # Run all recommendation engines concurrently and collect their results.
    with ThreadPoolExecutor() as executor:
        character_future = executor.submit(recommend, movie.movielens_id, top_n=5)
        story_future = executor.submit(recommend_story, movie.movielens_id, top_n=5)
        ppl_reco_future = executor.submit(recommend_dir, movie.movielens_id, top_n=5)
        budget_reco_future = executor.submit(recommend_budget, movie.movielens_id, top_n=5)
        keywords_future = executor.submit(recommend_keywords, movie.movielens_id, top_n=5)

        recommendations = character_future.result()
        story_recommendations = story_future.result()
        people_recommendations = ppl_reco_future.result()
        production_recommendations = budget_reco_future.result()
        keywords_recommendations = keywords_future.result()

    return render(request, "recommender/recommendations.html", {
        "movie": movie,
        "recommendations": recommendations,
        "story_recommendations": story_recommendations,
        "people_recommendations": people_recommendations,
        "production_recommendations": production_recommendations,
        "keywords_recommendations": keywords_recommendations,
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
    print(f"characters: {[c for c in movie.characters.all()]}")

    print("cast:")
    for mc in movie.moviecast_set.all():
        print(f"[{mc.order}] {mc.person.name} as {mc.character}")

    print("crew:")
    for mc in movie.moviecrew_set.all():
        print(f"{mc.department} / {mc.job}: {mc.person.name}")

    print("------------------------------------------------------------")

def movie_search_suggestions(request):
    query = request.GET.get("q", "").strip()
 
    if len(query) < 2:
        return JsonResponse({"results": []})
 
    matches = (
        Movie.objects
        .filter(title__icontains=query)
        .order_by("-popularity")[:20]
    )
 
    results = [
        {
            "id": movie.movielens_id,
            "title": movie.title,
            "year": movie.release_year,
            "poster_path": movie.poster_path,
            "cover_link": movie.cover_link,
        }
        for movie in matches
    ]
 
    return JsonResponse({"results": results})
