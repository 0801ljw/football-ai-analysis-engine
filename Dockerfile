FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
COPY data/demo_matches.json ./data/demo_matches.json
COPY scripts ./scripts
RUN python -m pip install --no-cache-dir -e . && chmod +x scripts/*.sh scripts/*.py
ENV WC_HOST=127.0.0.1 PORT=8787
EXPOSE 8787
CMD ["scripts/start.sh"]
