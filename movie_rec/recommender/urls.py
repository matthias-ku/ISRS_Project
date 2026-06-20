from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('movies/<int:pk>/', views.movie_detail_async, name='movie-detail'),
    path("api/movie-search/", views.movie_search_suggestions, name="movie-search-suggestions"),
]
