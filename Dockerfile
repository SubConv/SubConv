FROM python:3.13-alpine3.22 AS builder
LABEL name="subconv"

WORKDIR /app

RUN apk add --update-cache ca-certificates tzdata clang ccache bash curl unzip build-base && \
    apk upgrade --no-cache

# Nuitka rejects Alpine's patchelf 0.18.0. Build the supported version
# against the target architecture's musl rather than using a glibc binary.
RUN curl -fsSL https://github.com/NixOS/patchelf/releases/download/0.17.2/patchelf-0.17.2.tar.gz -o /tmp/patchelf.tar.gz && \
    echo "20427b718dd130e4b66d95072c2a2bd5e17232e20dad58c1bea9da81fae330e0  /tmp/patchelf.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/patchelf.tar.gz -C /tmp && \
    cd /tmp/patchelf-0.17.2 && ./configure && make -j2 && make install && \
    patchelf --version && rm -rf /tmp/patchelf*

ENV BUN_INSTALL=/root/.bun
ENV PATH=${BUN_INSTALL}/bin:${PATH}

RUN pip3 install uv

ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable --group build

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --group build

RUN --mount=type=cache,target=/root/.cache/Nuitka \
    uv run python -m nuitka --clang --onefile --standalone api.py && \
    chmod +x api.bin

RUN curl -fsSL https://bun.sh/install | bash -s -- bun-v1.3.11

RUN cd mainpage && bun install --frozen-lockfile && bun run build


FROM alpine:3.22

WORKDIR /app

RUN apk upgrade --no-cache

COPY --from=builder /app/api.bin /app/api.bin
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/mainpage/dist /app/mainpage/dist
COPY config.yaml.example /app/config.yaml.example
COPY template /app/template

EXPOSE 8080

ENTRYPOINT ["/app/api.bin"]
