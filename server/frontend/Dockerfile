FROM node:22-alpine AS build-stage
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY ./ .
RUN npm run build

FROM nginx:1.27-alpine AS production-stage
RUN apk add --no-cache curl \
    && mkdir -p /app
COPY --from=build-stage /app/dist /app
COPY nginx.conf /etc/nginx/nginx.conf
COPY security-headers.conf /etc/nginx/security-headers.conf

# The source key remains 0600 on the host. Assign the image copies directly to
# the unprivileged runtime user instead of weakening the host-side permissions.
COPY --chown=nginx:nginx --chmod=0444 certs/cert.pem /app/cert.pem
COPY --chown=nginx:nginx --chmod=0400 certs/key.pem /app/key.pem

USER nginx
