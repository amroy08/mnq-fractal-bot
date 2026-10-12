FROM python:3.13-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml /app/
COPY src/ /app/src/
COPY data/mnq_5m_real.csv /app/data/mnq_5m_real.csv

# Install bot package and runtime dependencies
RUN pip install --no-cache-dir -e .

EXPOSE 8080

CMD ["python", "-m", "mnq_fractal_bot.execution.live_paper_runner", "--host", "0.0.0.0", "--port", "8080"]
