FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 TZ=Asia/Tehran
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY config ./config
COPY migrations ./migrations

# Non-root: the only writable path this service needs is the database volume.
RUN useradd --create-home --uid 10001 monitor && mkdir -p /app/data && chown -R monitor /app/data
USER monitor
VOLUME ["/app/data"]

ENTRYPOINT ["market-monitor"]
CMD ["run-once", "--dry-run"]
