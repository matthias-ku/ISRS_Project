# Setup
# 0. Dirst download https://drive.google.com/file/d/1je77e0Lq8naVUsjoOzk5RuI2H3ceHlSz/view and extract the folder in the movie_rec folder -> movie_rec/extracted_content_ml-latest

# 1. Create and activate the virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_md

# 3. Apply database migrations (run inside the movie_rec/ folder)
python manage.py migrate

# 4. Import all movies from the JSON dataset (place the data in the folder /movie_rec/extracted_content_ml-latest/)(run inside the movie_rec/ folder)
python manage.py import_movies
# Optional: with limit
python manage.py import_movies --limit 100

# 5. (Optional) Create an admin user to browse data at /admin/ (run inside the movie_rec/ folder)
python manage.py createsuperuser

# 6. Pre-compute spaCy overview vectors for all movies (run inside the movie_rec/ folder)
python manage.py vectorize_overviews
# recompute already-vectorized movies
python manage.py vectorize_overviews --recompute

# 7. Pre-compute data dictionary (run inside the movie_rec/ folder)
python manage.py build_features

# 8. Start the dev server (run inside the movie_rec/ folder)
python manage.py runserver