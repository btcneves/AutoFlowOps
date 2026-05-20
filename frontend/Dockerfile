FROM node:20-slim AS build

LABEL org.opencontainers.image.title="AutoFlowOps Frontend" \
      org.opencontainers.image.description="React/TypeScript frontend for AutoFlowOps" \
      org.opencontainers.image.source="https://github.com/btcneves/autoflowops" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:20-slim AS runtime

WORKDIR /app

COPY --from=build /app/package*.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist

EXPOSE 3000

CMD ["npx", "vite", "preview", "--host", "--port", "3000", "--outDir", "dist"]
