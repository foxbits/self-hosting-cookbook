# syntax=docker/dockerfile:1

FROM rclone/rclone:1.76.0 AS rclone

FROM alpine:3.22

ARG TARGETARCH=amd64
ARG SUPERCRONIC_VERSION=0.2.51

RUN apk add --no-cache \
        ca-certificates \
        curl \
        docker-cli \
        python3 \
        py3-pip \
        restic \
        tini \
        tzdata \
    && case "${TARGETARCH}" in \
        amd64) \
            SUPERCRONIC_ARCH="amd64" ; \
            SUPERCRONIC_SHA1="1692066e350a88ff4d7d6474fe3c7a6c41ec5e89" ; \
            ;; \
        arm64) \
            SUPERCRONIC_ARCH="arm64" ; \
            SUPERCRONIC_SHA1="9d4c2000493215a1898502b2fc2dada3e8ea8c7a" ; \
            ;; \
        *) \
            echo "Unsupported architecture: ${TARGETARCH}" >&2 ; \
            exit 1 ; \
            ;; \
    esac \
    && curl -fsSL -o /usr/local/bin/supercronic \
        "https://github.com/aptible/supercronic/releases/download/v${SUPERCRONIC_VERSION}/supercronic-linux-${SUPERCRONIC_ARCH}" \
    && echo "${SUPERCRONIC_SHA1}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod 0755 /usr/local/bin/supercronic \
    && apk add --no-cache --virtual .apprise-build-deps gcc musl-dev python3-dev \
    && python3 -m pip install --no-cache-dir --break-system-packages apprise==1.9.5 \
    && apk del .apprise-build-deps

COPY --from=rclone /usr/local/bin/rclone /usr/local/bin/rclone
COPY src/backup_runner /app/backup_runner
COPY services.json /etc/backup/services.json

WORKDIR /app

ENV PATH="/usr/local/bin:${PATH}" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    RCLONE_CONFIG="/config/rclone/rclone.conf" \
    RESTIC_CACHE_DIR="/root/.cache/restic"

ENTRYPOINT ["/sbin/tini", "--", "python3", "-m", "backup_runner", "entrypoint"]
