FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    unzip \
    ripgrep \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g opencode-ai

ARG GEMINI_VERSION=v0.43.0
RUN curl -L \
    "https://github.com/google-gemini/gemini-cli/releases/download/${GEMINI_VERSION}/gemini-cli-bundle.zip" \
    -o /tmp/gemini.zip \
    && unzip /tmp/gemini.zip -d /opt/gemini-cli \
    && chmod +x /opt/gemini-cli/gemini.js \
    && ln -s /opt/gemini-cli/gemini.js /usr/local/bin/gemini \
    && rm /tmp/gemini.zip

ENV GEMINI_CLI_TRUST_WORKSPACE=true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

COPY src/ src/
COPY gui/ gui/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "-m", "src.main"]
