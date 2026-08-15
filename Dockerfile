FROM python:3.11-slim

WORKDIR /app

# Configure apt to retry downloads
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80-retries

# Dynamically find and switch deb.debian.org to the stable cdn-fastly mirror
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's/deb.debian.org/cdn-fastly.deb.debian.org/g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/cdn-fastly.deb.debian.org/g' /etc/apt/sources.list; \
    fi

# Install git with fallback options
RUN apt-get update && \
    apt-get install -y --fix-missing --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
COPY prod_assistant ./prod_assistant

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# run uvicorn properly on 0.0.0.0:8000
CMD ["bash", "-c", "python prod_assistant/mcp_servers/product_search_server.py & uvicorn prod_assistant.router.main:app --host 0.0.0.0 --port 8000 --workers 2"]