FROM --platform=$BUILDPLATFORM python:3.11.8-alpine3.19 AS builder
LABEL name="subconv"

WORKDIR /app

COPY . .

# Install dependencies
RUN apk add --update-cache ca-certificates tzdata patchelf clang ccache

# Insall python and dependencies
RUN pip3 install -r requirements.txt && \
    pip3 install nuitka

# Use nuikta to compile the python code
RUN --mount=type=cache,target=/root/.cache/Nuitka \
    python3 -m nuitka --clang --onefile --standalone api.py && \
    chmod +x api.bin


FROM alpine

WORKDIR /app

COPY --from=builder /app/api.bin /app/api.bin
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY static /app/static
COPY config.yaml /app/config.yaml

EXPOSE 8080

ENTRYPOINT ["/app/api.bin"]
