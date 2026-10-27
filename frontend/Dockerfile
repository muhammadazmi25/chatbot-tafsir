# Dockerfile simpel — langsung serve folder dist/ yang sudah di-build
# Tidak perlu Node.js di VPS, cukup Nginx
FROM nginx:1.27-alpine

# Hapus config default nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copy hasil build Vite (dist/) ke root Nginx
COPY dist /usr/share/nginx/html

# Fix permission — file dari Windows sering restrictive
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

# Copy nginx config SPA
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
