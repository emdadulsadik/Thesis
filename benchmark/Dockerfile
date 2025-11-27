FROM python:3.9-slim
RUN pip install pandas matplotlib

COPY ./ /app/
WORKDIR /app

ENTRYPOINT ["python", "benchmark.py"]