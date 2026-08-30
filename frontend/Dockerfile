FROM node:22-slim

WORKDIR /app
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --config.dangerously-allow-all-builds=true

COPY . .
ARG NEXT_PUBLIC_API_ORIGIN=http://localhost:8000
ENV NEXT_PUBLIC_API_ORIGIN=$NEXT_PUBLIC_API_ORIGIN
RUN pnpm build

EXPOSE 3000

ENV NODE_ENV=production
CMD ["pnpm", "start"]
