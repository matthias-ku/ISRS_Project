from django.core.management.base import BaseCommand
from recommender.models import Movie

SPACY_MODEL = "en_core_web_md"
BATCH_SIZE = 256

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--recompute", action="store_true", default=False)

    def handle(self, *args, **options):
        try:
            import numpy as np
            import spacy
        except ImportError as exc:
            self.stderr.write(f"Missing dependency: {exc}")
            self.stderr.write("Install: pip install spacy numpy && python -m spacy download en_core_web_md")
            return

        try:
            nlp = spacy.load(SPACY_MODEL, disable=["ner", "parser", "tagger", "lemmatizer"])
        except OSError:
            self.stderr.write("Model not found. Run: python -m spacy download en_core_web_md")
            return

        movies = Movie.objects.only("movielens_id", "overview", "overview_vector")
        if not options["recompute"]:
            movies = movies.filter(overview_vector__isnull=True)

        total = movies.count()
        if total == 0:
            self.stdout.write("All movies already have vectors, --recompute to update.")
            return

        self.stdout.write(f"Vectorizing {total} movies")

        batch = []
        texts = []
        processed = 0

        for movie in movies.iterator(chunk_size=BATCH_SIZE):
            batch.append(movie)
            texts.append(movie.overview or "")

            if len(batch) >= BATCH_SIZE:
                processed += save_vectors(nlp, np, batch, texts)
                self.stdout.write(f"  {processed}/{total}")
                batch, texts = [], []

        if batch:
            processed += save_vectors(nlp, np, batch, texts)

        self.stdout.write(f"Vectorized {processed} movies.")


def save_vectors(nlp, np, movies, texts):
    for movie, doc in zip(movies, nlp.pipe(texts, batch_size=BATCH_SIZE)):
        movie.overview_vector = doc.vector.astype(np.float32).tobytes()
    Movie.objects.bulk_update(movies, ["overview_vector"])
    return len(movies)
