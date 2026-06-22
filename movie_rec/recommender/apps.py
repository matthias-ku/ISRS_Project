from django.apps import AppConfig



class RecommenderConfig(AppConfig):
    name = 'recommender'
    def ready(self):
        from .features import load_all_features
        load_all_features()
