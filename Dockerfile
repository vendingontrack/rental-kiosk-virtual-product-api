FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY examples/ examples/

ENV PORT=8099
ENV API_KEY=test-api-key
ENV DATA_FILE=examples/golf.json
ENV RESPONSE_DELAY_MS=0
ENV FAIL_PURCHASE=false

EXPOSE 8099

CMD ["python", "main.py"]
