# Procfile
web: gunicorn src.main:wsgi_app --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120
