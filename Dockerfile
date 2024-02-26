FROM python:3
WORKDIR /app
COPY app.py ./
COPY pit38/ ./pit38/
COPY templates/ ./templates/
COPY pyproject.toml ./
COPY poetry.lock ./
RUN pip install poetry && poetry install
CMD ["poetry", "run", "flask", "run", "--host", "0.0.0.0", "--port", "5555"]
