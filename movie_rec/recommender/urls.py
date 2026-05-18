from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('movies/<int:pk>/', views.movie_detail, name='movie-detail'),
]
