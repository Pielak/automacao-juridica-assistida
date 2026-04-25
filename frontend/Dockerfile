# =============================================================================
# Dockerfile — Frontend do sistema Automação Jurídica Assistida
# Build multi-stage: compilação com Node + servir estático com Nginx
# =============================================================================

# ---------------------------------------------------------------------------
# Estágio 1: Instalação de dependências e build da aplicação React/Vite
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Metadados da imagem
LABEL maintainer="Equipe Automação Jurídica Assistida"
LABEL description="Build stage — compilação do frontend React + Vite + TypeScript"

# Diretório de trabalho dentro do container
WORKDIR /app

# Copiar apenas arquivos de manifesto primeiro para aproveitar cache de camadas
# Isso evita reinstalar dependências quando só o código-fonte muda
COPY package.json package-lock.json* yarn.lock* pnpm-lock.yaml* ./

# Instalar dependências de produção e desenvolvimento (necessárias para o build)
# Usar --frozen-lockfile quando disponível para garantir reprodutibilidade
RUN \
  if [ -f pnpm-lock.yaml ]; then \
    corepack enable pnpm && pnpm install --frozen-lockfile; \
  elif [ -f yarn.lock ]; then \
    yarn install --frozen-lockfile; \
  elif [ -f package-lock.json ]; then \
    npm ci; \
  else \
    echo "Nenhum lockfile encontrado. Executando npm install..." && npm install; \
  fi

# Copiar o restante do código-fonte da aplicação
COPY . .

# Variáveis de ambiente para o build (podem ser sobrescritas via --build-arg)
# VITE_API_BASE_URL: URL base da API backend
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Executar o build de produção (tsc + vite build conforme package.json)
RUN \
  if [ -f pnpm-lock.yaml ]; then \
    corepack enable pnpm && pnpm run build; \
  elif [ -f yarn.lock ]; then \
    yarn build; \
  else \
    npm run build; \
  fi

# ---------------------------------------------------------------------------
# Estágio 2: Servir arquivos estáticos com Nginx
# ---------------------------------------------------------------------------
FROM nginx:1.25-alpine AS production

LABEL maintainer="Equipe Automação Jurídica Assistida"
LABEL description="Produção — Nginx servindo SPA React com headers de segurança"

# Remover configuração padrão do Nginx
RUN rm -rf /etc/nginx/conf.d/default.conf /usr/share/nginx/html/*

# Copiar configuração customizada do Nginx com:
# - Headers de segurança (CSP, X-Frame-Options, etc.)
# - Proxy reverso para API backend
# - Fallback para index.html (SPA routing)
# - Compressão gzip
# - Cache de assets estáticos
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar artefatos do build (Vite gera em dist/ por padrão)
COPY --from=builder /app/dist /usr/share/nginx/html

# Criar usuário não-root para execução segura do Nginx
# Alpine já possui o usuário nginx, mas garantimos permissões corretas
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# Expor porta 80 (HTTP)
# Em produção, TLS deve ser terminado no load balancer ou proxy externo
EXPOSE 80

# Healthcheck para orquestradores (Docker Compose, Kubernetes, etc.)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Executar Nginx em foreground (necessário para containers Docker)
CMD ["nginx", "-g", "daemon off;"]
