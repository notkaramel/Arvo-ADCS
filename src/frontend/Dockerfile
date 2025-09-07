FROM oven/bun:latest AS builder

WORKDIR /app
COPY . .
RUN bun install
RUN bun run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]