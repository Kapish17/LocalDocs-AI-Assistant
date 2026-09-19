# LocalDocs AI Assistant — React frontend container image.
#
# Build stage compiles the Vite app; serve stage is a small nginx image.
# Vite environment variables (VITE_API_URL) are baked into the JS bundle at
# BUILD time, not read at container startup — pass the backend's URL via
# --build-arg when building this image for a specific environment:
#
#   docker build -f frontend/Dockerfile -t localdocs-frontend \
#     --build-arg VITE_API_URL=https://your-backend-url \
#     frontend
#
# Cloud Run-ready: the container listens on the PORT env var Cloud Run
# injects at runtime (nginx doesn't support runtime env vars natively, so a
# tiny entrypoint script substitutes it into the nginx config at startup).

# ---- Build ----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- Serve ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/conf.d/default.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV PORT=8080
EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]
