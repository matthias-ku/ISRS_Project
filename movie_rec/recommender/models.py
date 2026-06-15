from django.db import models

# Loaded once
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_md", disable=["ner", "parser", "tagger", "lemmatizer"])
    return _nlp


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Keyword(models.Model):
    name = models.CharField(max_length=255, unique=True)
    tmdb_id = models.IntegerField(null=True, blank=True, unique=True)

    def __str__(self):
        return self.name


class Person(models.Model):
    name = models.CharField(max_length=255)
    tmdb_id = models.IntegerField(null=True, blank=True, unique=True)
    profile_path = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.name


class Movie(models.Model):
    movielens_id = models.IntegerField(primary_key=True)
    tmdb_id = models.IntegerField(null=True, blank=True, db_index=True)
    imdb_id = models.CharField(max_length=20, null=True, blank=True)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, null=True, blank=True)
    release_year = models.CharField(max_length=4, null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    runtime = models.IntegerField(null=True, blank=True)
    overview = models.TextField(null=True, blank=True)
    tagline = models.CharField(max_length=500, null=True, blank=True)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    backdrop_path = models.CharField(max_length=255, null=True, blank=True)
    popularity = models.FloatField(null=True, blank=True)
    vote_average = models.FloatField(null=True, blank=True)
    vote_count = models.IntegerField(null=True, blank=True)
    avg_rating = models.FloatField(null=True, blank=True)
    num_ratings = models.IntegerField(null=True, blank=True)
    budget = models.BigIntegerField(null=True, blank=True)
    revenue = models.BigIntegerField(null=True, blank=True)
    adult = models.BooleanField(default=False)
    original_language = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)
    overview_vector = models.BinaryField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True)
    directors = models.ManyToManyField(Person, related_name='directed', blank=True)
    cast = models.ManyToManyField(Person, through='MovieCast', related_name='acted_in', blank=True)
    crew = models.ManyToManyField(Person, through='MovieCrew', related_name='crewed_in', blank=True)

    def get_overview_vector(self):
        #Computes and persists the vector on first call if not yet stored
        import numpy as np

        if self.overview_vector:
            return np.frombuffer(bytes(self.overview_vector), dtype=np.float32)

        if not self.overview:
            return None

        nlp = _get_nlp()
        vector = nlp(self.overview).vector.astype(np.float32)
        self.overview_vector = vector.tobytes()
        Movie.objects.filter(pk=self.pk).update(overview_vector=self.overview_vector)
        return vector

    def __str__(self):
        return self.title


class MovieCast(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    character = models.CharField(max_length=255, null=True, blank=True)
    order = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['order']


class MovieCrew(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, null=True, blank=True)
    job = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['department', 'job']

    def __str__(self):
        return f"{self.person.name} - {self.job}"
