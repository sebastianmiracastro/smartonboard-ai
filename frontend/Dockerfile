# ---- deps: instala node_modules (compartido por dev y prod) ----
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ---- dev: hot-reload con "next dev" (usado por docker-compose.override.yml) ----
FROM node:20-alpine AS dev
WORKDIR /app
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "run", "dev"]

# ---- builder: build de producción ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner: imagen final de producción ----
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
