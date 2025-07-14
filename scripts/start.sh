#!/bin/bash

echo "🚀 Report Generator를 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 함수 정의
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. 환경 변수 파일 확인
if [ ! -f .env ]; then
    print_error ".env 파일이 없습니다."
    print_status "scripts/setup.sh를 먼저 실행해주세요."
    exit 1
fi

# 2. Docker 확인
if ! command -v docker &> /dev/null; then
    print_error "Docker가 설치되어 있지 않습니다."
    print_status "Docker를 설치한 후 다시 시도해주세요."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose가 설치되어 있지 않습니다."
    print_status "Docker Compose를 설치한 후 다시 시도해주세요."
    exit 1
fi

# 3. 포트 확인
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

print_status "포트 사용 가능 여부를 확인합니다..."

if ! check_port 7000; then
    print_warning "포트 7000이 이미 사용 중입니다."
fi

if ! check_port 7080; then
    print_warning "포트 7080이 이미 사용 중입니다."
fi

# 4. 기존 컨테이너 정리
print_status "기존 컨테이너를 정리합니다..."
docker-compose down 2>/dev/null || true

# 5. 이미지 빌드 및 서비스 시작
print_status "Docker 이미지를 빌드하고 서비스를 시작합니다..."
if docker-compose up --build -d; then
    print_success "서비스가 성공적으로 시작되었습니다!"
else
    print_error "서비스 시작에 실패했습니다."
    print_status "로그를 확인하려면 'docker-compose logs' 명령을 실행하세요."
    exit 1
fi

# 6. 서비스 상태 확인
print_status "서비스 상태를 확인합니다..."
sleep 10

# 헬스체크
health_check() {
    if curl -s -f http://localhost:7080/health > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

print_status "헬스체크를 수행합니다..."
for i in {1..30}; do
    if health_check; then
        print_success "서비스가 정상적으로 실행 중입니다!"
        break
    else
        if [ $i -eq 30 ]; then
            print_error "서비스 헬스체크에 실패했습니다."
            print_status "컨테이너 로그를 확인해주세요: docker-compose logs"
            exit 1
        fi
        echo -n "."
        sleep 2
    fi
done

# 7. 서비스 정보 출력
echo ""
print_success "🎉 Report Generator가 성공적으로 시작되었습니다!"
echo ""
echo -e "${BLUE}📋 서비스 정보:${NC}"
echo -e "  🌐 웹 인터페이스: ${GREEN}http://localhost:7080${NC}"
echo -e "  📚 API 문서: ${GREEN}http://localhost:7080/api/docs${NC}"
echo -e "  📊 생성된 리포트: ${GREEN}http://localhost:7080/reports/${NC}"
echo -e "  🔍 헬스체크: ${GREEN}http://localhost:7080/health${NC}"
echo ""
echo -e "${BLUE}🔧 유용한 명령어:${NC}"
echo "  - 로그 확인: docker-compose logs -f"
echo "  - 서비스 중지: docker-compose down"
echo "  - 서비스 재시작: docker-compose restart"
echo "  - 컨테이너 상태 확인: docker-compose ps"
echo ""
echo -e "${BLUE}💡 사용법:${NC}"
echo "1. 웹 브라우저에서 http://localhost:7080 접속"
echo "2. 원하는 리포트 내용을 자연어로 입력"
echo "3. '리포트 생성하기' 버튼 클릭"
echo "4. 생성된 HTML 리포트 확인"
echo ""
echo -e "${YELLOW}⚠️  문제가 발생하면:${NC}"
echo "  - .env 파일의 OpenRouter API 키 확인"
echo "  - docker-compose logs로 오류 로그 확인"
echo "  - 7000, 7080 포트가 사용 가능한지 확인"
echo ""

# 8. 브라우저에서 자동으로 열기 (macOS/Linux)
if command -v open &> /dev/null; then
    print_status "브라우저에서 웹 인터페이스를 엽니다..."
    open http://localhost:7080
elif command -v xdg-open &> /dev/null; then
    print_status "브라우저에서 웹 인터페이스를 엽니다..."
    xdg-open http://localhost:7080
fi 