# syntax=docker/dockerfile:1
FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.13-slim
RUN useradd --create-home --uid 10001 pulsewatch && mkdir /data && chown pulsewatch /data
COPY --from=build /install /usr/local
USER pulsewatch
WORKDIR /home/pulsewatch
ENV PULSEWATCH_DB_PATH=/data/pulsewatch.db \
    PULSEWATCH_TARGETS_FILE=/config/targets.yaml \
    PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1
ENTRYPOINT ["pulsewatch"]
