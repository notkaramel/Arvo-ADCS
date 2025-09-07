FROM oven/bun:latest AS builder

WORKDIR /app
COPY . .
RUN bun install
RUN bun run build
CMD bun run serve --host 0.0.0.0 --port 80