# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ── Stage 2: serve with nginx ─────────────────────────────────────────────────
FROM nginx:stable-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy the built React app
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config: serve SPA and proxy /api calls to the backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
