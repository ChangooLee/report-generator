FROM nginx:alpine

# Nginx 설정 파일 복사
COPY config/nginx.conf /etc/nginx/nginx.conf

# 정적 파일 디렉토리 생성
RUN mkdir -p /usr/share/nginx/html/reports \
    && mkdir -p /usr/share/nginx/html/static

# 기본 인덱스 페이지 생성
RUN echo '<!DOCTYPE html>' > /usr/share/nginx/html/index.html && \
    echo '<html><head><title>Report Generator</title></head>' >> /usr/share/nginx/html/index.html && \
    echo '<body><h1>Report Generator Service</h1>' >> /usr/share/nginx/html/index.html && \
    echo '<p>API 문서: <a href="/api/docs">/api/docs</a></p>' >> /usr/share/nginx/html/index.html && \
    echo '<p>리포트: <a href="/reports/">/reports/</a></p>' >> /usr/share/nginx/html/index.html && \
    echo '</body></html>' >> /usr/share/nginx/html/index.html

# 포트 노출
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"] 