from django.contrib import admin
from .models import Genre, Keyword, Person, Movie, MovieCast


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ['name', 'tmdb_id']


class MovieCastInline(admin.TabularInline):
    model = MovieCast
    extra = 0
    raw_id_fields = ['person']


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'release_year', 'avg_rating', 'num_ratings', 'vote_average']
    list_filter = ['genres', 'release_year', 'original_language']
    search_fields = ['title', 'original_title', 'imdb_id']
    filter_horizontal = ['genres', 'keywords', 'directors']
    inlines = [MovieCastInline]
