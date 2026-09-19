#!/bin/sh
# Substitutes only ${PORT} into the nginx config (not nginx's own $uri etc.)
# so the container listens on whatever port Cloud Run/docker-compose assigns.
set -e
envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
