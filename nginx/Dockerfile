# =============================================================================
# Dockerfile — Nginx para Automação Jurídica Assistida
# Imagem Nginx com configuração customizada, headers de segurança e suporte
# a certificados TLS. Serve a SPA React como arquivos estáticos e atua como
# proxy reverso para a API FastAPI.
# =============================================================================

# ---------------------------------------------------------------------------
# Estágio 1: Build da SPA React (opcional — pode ser substituído por COPY
# de artefatos pré-compilados via CI/CD pipeline)
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copia apenas arquivos de dependência primeiro para aproveitar cache do Docker
COPY frontend/package.json frontend/package-lock.json* frontend/yarn.lock* ./

# Instala dependências
RUN npm ci --prefer-offline --no-audit || yarn install --frozen-lockfile

# Copia o restante do código fonte do frontend
COPY frontend/ ./

# Build de produção com Vite
RUN npm run build || yarn build

# ---------------------------------------------------------------------------
# Estágio 2: Imagem Nginx de produção
# ---------------------------------------------------------------------------
FROM nginx:1.25-alpine AS production

# Metadados da imagem
LABEL maintainer="Equipe Automação Jurídica Assistida"
LABEL description="Nginx — proxy reverso e servidor de arquivos estáticos para a plataforma de Automação Jurídica Assistida"
LABEL version="1.0.0"

# Variáveis de ambiente com valores padrão (podem ser sobrescritas no docker-compose)
ENV NGINX_WORKER_PROCESSES=auto
ENV NGINX_WORKER_CONNECTIONS=1024
ENV API_UPSTREAM_HOST=api
ENV API_UPSTREAM_PORT=8000
ENV SERVER_NAME=localhost
ENV SSL_ENABLED=false

# ---------------------------------------------------------------------------
# Instalação de dependências do sistema
# ---------------------------------------------------------------------------
RUN apk update && \
    apk add --no-cache \
        curl \
        openssl \
        ca-certificates \
        tzdata && \
    # Define timezone para São Paulo (padrão jurídico brasileiro)
    cp /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime && \
    echo "America/Sao_Paulo" > /etc/timezone && \
    # Limpeza de cache do apk
    rm -rf /var/cache/apk/*

# ---------------------------------------------------------------------------
# Criação de diretórios necessários
# ---------------------------------------------------------------------------
RUN mkdir -p /etc/nginx/ssl && \
    mkdir -p /etc/nginx/conf.d && \
    mkdir -p /var/log/nginx && \
    mkdir -p /var/cache/nginx && \
    mkdir -p /usr/share/nginx/html && \
    mkdir -p /etc/nginx/snippets

# ---------------------------------------------------------------------------
# Geração de certificados autoassinados para desenvolvimento
# Em produção, montar certificados reais via volume ou usar Let's Encrypt
# ---------------------------------------------------------------------------
RUN openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=BR/ST=SP/L=SaoPaulo/O=AutomacaoJuridica/OU=TI/CN=localhost" && \
    # Gera parâmetros Diffie-Hellman para segurança TLS aprimorada
    openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

# ---------------------------------------------------------------------------
# Copia a configuração customizada do Nginx
# ---------------------------------------------------------------------------
# Remove a configuração padrão do Nginx
RUN rm -f /etc/nginx/conf.d/default.conf && \
    rm -f /etc/nginx/nginx.conf

# Copia a configuração principal do Nginx (peer: nginx/nginx.conf)
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# ---------------------------------------------------------------------------
# Snippet de configuração SSL reutilizável
# ---------------------------------------------------------------------------
RUN printf '%s\n' \
    '# Snippet de configuração SSL — Automação Jurídica Assistida' \
    '# Parâmetros de segurança TLS seguindo boas práticas (Mozilla Modern)' \
    '' \
    'ssl_certificate /etc/nginx/ssl/selfsigned.crt;' \
    'ssl_certificate_key /etc/nginx/ssl/selfsigned.key;' \
    'ssl_dhparam /etc/nginx/ssl/dhparam.pem;' \
    '' \
    '# Protocolos e cifras — apenas TLS 1.2+ (requisito LGPD/compliance)' \
    'ssl_protocols TLSv1.2 TLSv1.3;' \
    'ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;' \
    'ssl_prefer_server_ciphers off;' \
    '' \
    '# Cache de sessão SSL' \
    'ssl_session_cache shared:SSL:10m;' \
    'ssl_session_timeout 1d;' \
    'ssl_session_tickets off;' \
    '' \
    '# OCSP Stapling (habilitar quando usar certificados reais)' \
    '# ssl_stapling on;' \
    '# ssl_stapling_verify on;' \
    '# ssl_trusted_certificate /etc/nginx/ssl/chain.pem;' \
    > /etc/nginx/snippets/ssl-params.conf

# ---------------------------------------------------------------------------
# Snippet de headers de segurança
# ---------------------------------------------------------------------------
RUN printf '%s\n' \
    '# Snippet de headers de segurança — Automação Jurídica Assistida' \
    '# Headers obrigatórios para compliance e proteção da aplicação' \
    '' \
    '# Previne clickjacking' \
    'add_header X-Frame-Options "SAMEORIGIN" always;' \
    '' \
    '# Previne MIME type sniffing' \
    'add_header X-Content-Type-Options "nosniff" always;' \
    '' \
    '# Habilita filtro XSS do navegador' \
    'add_header X-XSS-Protection "1; mode=block" always;' \
    '' \
    '# Política de referrer restritiva' \
    'add_header Referrer-Policy "strict-origin-when-cross-origin" always;' \
    '' \
    '# HSTS — força HTTPS por 1 ano (habilitar em produção)' \
    '# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;' \
    '' \
    '# Política de permissões (desabilita recursos desnecessários)' \
    'add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;' \
    '' \
    '# Content Security Policy — ajustar conforme necessidade da SPA' \
    '# TODO: Refinar CSP após definição dos design tokens (G005 ADR)' \
    "add_header Content-Security-Policy \"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'self';\" always;" \
    > /etc/nginx/snippets/security-headers.conf

# ---------------------------------------------------------------------------
# Copia os arquivos estáticos da SPA React (build do estágio 1)
# ---------------------------------------------------------------------------
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html

# ---------------------------------------------------------------------------
# Ajuste de permissões — execução como usuário não-root
# ---------------------------------------------------------------------------
# Garante que o usuário nginx tenha acesso aos diretórios necessários
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/ssl && \
    chmod 600 /etc/nginx/ssl/selfsigned.key && \
    chmod 644 /etc/nginx/ssl/selfsigned.crt && \
    chmod 644 /etc/nginx/ssl/dhparam.pem && \
    # Cria arquivo de PID com permissão para usuário nginx
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

# ---------------------------------------------------------------------------
# Healthcheck — verificação de saúde do container
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# ---------------------------------------------------------------------------
# Exposição de portas
# ---------------------------------------------------------------------------
# Porta HTTP (redirecionamento para HTTPS em produção)
EXPOSE 80

# Porta HTTPS
EXPOSE 443

# ---------------------------------------------------------------------------
# Execução como usuário não-root (segurança)
# Nota: requer que nginx.conf use 'listen' em portas > 1024 ou que
# o container tenha CAP_NET_BIND_SERVICE. Em produção, avaliar uso
# de portas altas (8080/8443) mapeadas externamente.
# ---------------------------------------------------------------------------
# TODO: Descomentar após ajustar nginx.conf para portas não-privilegiadas
# USER nginx

# ---------------------------------------------------------------------------
# Comando de inicialização
# ---------------------------------------------------------------------------
# Executa Nginx em foreground (necessário para Docker)
CMD ["nginx", "-g", "daemon off;"]
