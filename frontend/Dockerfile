
#BUILDER
FROM node:22-alpine AS builder

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install

COPY frontend/. .


RUN npm run build

#RUNNER 
FROM node:22-alpine AS runner

WORKDIR /app


ENV NODE_ENV production


ENV PORT 8080

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json


EXPOSE 8080

CMD ["npm", "start"]