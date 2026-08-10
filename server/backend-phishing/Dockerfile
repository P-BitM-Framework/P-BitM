FROM python:3.11-slim

WORKDIR /app

# Install the public reverse proxy and health-check client.
RUN apt-get update && \
    apt-get install -y nginx curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 bitm \
    && useradd --uid 1000 --gid bitm --create-home --shell /usr/sbin/nologin bitm \
    && install -d -o bitm -g bitm /tmp/nginx

# Copy the campaign application source.
COPY --chown=bitm:bitm app/. .

# Install Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Install the public gateway configuration.
COPY --chown=bitm:bitm nginx.conf /etc/nginx/nginx.conf
RUN chown bitm:bitm /etc/nginx

# Install the entry point that couples nginx and the Python application.
COPY --chown=bitm:bitm entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER bitm

CMD ["/entrypoint.sh"]
