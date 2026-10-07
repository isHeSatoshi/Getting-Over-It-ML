FROM python:3.11-slim-bookworm
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    RL_CHROME_BINARY=/usr/bin/chromium RL_CHROMEDRIVER=/usr/bin/chromedriver \
    RL_CHROME_CONTAINER=1 RL_CHROME_NO_SANDBOX=1 HOME=/home/user PATH=/home/user/.local/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium chromium-driver git nodejs fonts-liberation ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 user \
    && mkdir -p /home/user/app && chown user:user /home/user/app
WORKDIR /home/user/app
COPY requirements-research.txt requirements-space.txt ./
RUN pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements-research.txt -r requirements-space.txt
COPY --chown=user:user . .
USER user
EXPOSE 7860
CMD ["python", "-m", "deploy.space_worker"]
