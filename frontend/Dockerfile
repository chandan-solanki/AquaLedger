# syntax=docker/dockerfile:1

# Sprint 18 Session 3 - production image for the Next.js frontend, built
# around `output: "standalone"` (next.config.ts): the final stage ships
# only the traced subset of node_modules `next build` determined this app
# actually needs, not the full dependency tree - meaningfully smaller on a
# 1 vCPU / 6 GB VPS.
#
# NOT build-verified in this session - no Docker daemon was available in
# this development environment. `npm run build` itself (without Docker)
# WAS run and its `.next/standalone` output was verified directly - see
# DEPLOYMENT.md / the Session 3 report for that verification. Treat the
# first real `docker build` on the deployment host as verification of
# this file specifically.

FROM node:22-slim AS base

FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* variables are inlined into the client bundle at build
# time, not read at container-start time - even though every current
# consumer of NEXT_PUBLIC_API_URL happens to be server-side code (the BFF
# layer, never actually shipped to the browser bundle), Next.js still
# bakes it in at this step. This means the image must be rebuilt (not
# just restarted with new env vars) if the backend URL ever changes -
# call this out explicitly in DEPLOYMENT.md rather than silently.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_APP_NAME
ARG NEXT_PUBLIC_APP_ENV
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL} \
    NEXT_PUBLIC_APP_NAME=${NEXT_PUBLIC_APP_NAME} \
    NEXT_PUBLIC_APP_ENV=${NEXT_PUBLIC_APP_ENV}

RUN npm run build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN groupadd --system --gid 1001 nodejs \
    && useradd --system --uid 1001 --gid nodejs nextjs

COPY --from=builder /app/public ./public
# .next/standalone already contains its own traced node_modules and
# server.js - .next/static (client-side assets: JS chunks, CSS) is
# deliberately NOT included in .next/standalone by Next.js's own design
# and must be copied alongside it, per Next.js's documented standalone
# output pattern.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
