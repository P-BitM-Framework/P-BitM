FROM python:3.11-slim

WORKDIR /app

RUN groupadd --gid 1000 bitm \
    && useradd --uid 1000 --gid bitm --create-home --shell /usr/sbin/nologin bitm

# Install Python dependencies before copying the source for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY --chown=bitm:bitm . .

# Install the container entry point.
COPY --chown=bitm:bitm entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER bitm

CMD ["/entrypoint.sh"]
