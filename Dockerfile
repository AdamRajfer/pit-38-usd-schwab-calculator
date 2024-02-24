FROM python:3
WORKDIR /app
COPY app.py ./
COPY templates/ ./templates/
COPY requirements.txt ./
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
