FROM nginx:alpine

# Nginx 설정 파일 복사
COPY config/nginx.conf /etc/nginx/nginx.conf

# 정적 파일들 복사
COPY static/ /usr/share/nginx/html/static/
COPY frontend/ /usr/share/nginx/html/frontend/

# 포트 노출
EXPOSE 80

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]