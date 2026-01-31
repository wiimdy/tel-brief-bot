#!/bin/bash
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================"
echo "  Telegram Brief Bot EC2 Deploy"
echo "  (Docker + Git)"
echo "======================================"
echo ""

# EC2 Configuration
INSTANCE_ID="${EC2_INSTANCE_ID:-i-0c4ba36a98b543bd6}"
AWS_REGION="${AWS_REGION:-ap-northeast-2}"
DEPLOY_PATH="/opt/tel-brief-bot"
GIT_REPO="${GIT_REPO:-https://github.com/wiimdy/tel-brief-bot.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"

# 1. Check EC2 instance status
echo -e "${BLUE}[1/3] EC2 인스턴스 상태 확인 중...${NC}"
INSTANCE_STATE=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$AWS_REGION" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>/dev/null || echo "error")

if [ "$INSTANCE_STATE" != "running" ]; then
    echo -e "${RED}EC2 인스턴스가 실행 중이 아닙니다: $INSTANCE_STATE${NC}"
    exit 1
fi
echo -e "${GREEN}EC2 인스턴스 실행 중${NC}"

# 2. Push local changes to git first
echo ""
echo -e "${BLUE}[2/3] Git에 최신 코드 푸시...${NC}"
cd "$(dirname "$0")/.."
git add -A
git diff --cached --quiet || git commit -m "Deploy $(date '+%Y-%m-%d %H:%M:%S')"
git push origin "$GIT_BRANCH" || echo "Push failed or no changes"
echo -e "${GREEN}Git 푸시 완료${NC}"

# 3. Deploy to EC2 via SSM
echo ""
echo -e "${BLUE}[3/3] EC2 배포 중 (Docker)...${NC}"

aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --region "$AWS_REGION" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=[
        "set -e",
        "echo \"=== Telegram Brief Bot Docker 배포 시작 ===\"",

        "# Add 2GB swap if not exists (for t3.micro)",
        "if [ ! -f /swapfile ]; then",
        "  echo \"Creating swap file...\"",
        "  sudo fallocate -l 2G /swapfile",
        "  sudo chmod 600 /swapfile",
        "  sudo mkswap /swapfile",
        "  sudo swapon /swapfile",
        "  echo \"/swapfile none swap sw 0 0\" | sudo tee -a /etc/fstab",
        "fi",

        "# Install Docker if not exists",
        "if ! command -v docker &> /dev/null; then",
        "  echo \"Installing Docker...\"",
        "  curl -fsSL https://get.docker.com | sudo sh",
        "  sudo usermod -aG docker ssm-user",
        "fi",

        "# Install Docker Compose plugin",
        "if ! docker compose version &> /dev/null; then",
        "  echo \"Installing Docker Compose...\"",
        "  sudo apt-get update && sudo apt-get install -y docker-compose-plugin || true",
        "fi",

        "# Install git if not exists",
        "if ! command -v git &> /dev/null; then",
        "  sudo apt-get update && sudo apt-get install -y git",
        "fi",

        "# Clone or pull repository",
        "if [ -d '"$DEPLOY_PATH"' ]; then",
        "  echo \"Pulling latest changes...\"",
        "  cd '"$DEPLOY_PATH"'",
        "  sudo git fetch origin",
        "  sudo git reset --hard origin/'"$GIT_BRANCH"'",
        "else",
        "  echo \"Cloning repository...\"",
        "  sudo git clone -b '"$GIT_BRANCH"' '"$GIT_REPO"' '"$DEPLOY_PATH"'",
        "  cd '"$DEPLOY_PATH"'",
        "fi",

        "# Create necessary directories",
        "sudo mkdir -p data logs sessions",
        "sudo chmod -R 777 data logs sessions",

        "# Stop existing container",
        "sudo docker compose down 2>/dev/null || sudo docker-compose down 2>/dev/null || true",

        "# Build and start with Docker Compose",
        "sudo docker compose build --no-cache || sudo docker-compose build --no-cache",
        "sudo docker compose up -d || sudo docker-compose up -d",

        "# Health check",
        "sleep 5",
        "sudo docker compose ps || sudo docker-compose ps",

        "echo \"=== 배포 완료 ===\"",
        "sudo docker compose logs --tail=20 || sudo docker-compose logs --tail=20"
    ]' \
    --output json > /tmp/ssm-bot-command.json

COMMAND_ID=$(cat /tmp/ssm-bot-command.json | python3 -c "import sys, json; print(json.load(sys.stdin)['Command']['CommandId'])")
echo -e "${YELLOW}명령 실행 대기 중... (Command ID: $COMMAND_ID)${NC}"

# Wait for command completion
sleep 90

# Check command result
echo ""
echo -e "${BLUE}배포 결과 확인 중...${NC}"
aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$AWS_REGION" \
    --query 'StandardOutputContent' \
    --output text 2>/dev/null || echo "결과 조회 중..."

STATUS=$(aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$AWS_REGION" \
    --query 'Status' \
    --output text 2>/dev/null || echo "Unknown")

if [ "$STATUS" = "Success" ]; then
    echo -e "${GREEN}배포 성공!${NC}"
else
    echo -e "${YELLOW}Status: $STATUS${NC}"
    echo "에러 확인:"
    aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --region "$AWS_REGION" \
        --query 'StandardErrorContent' \
        --output text 2>/dev/null
fi

echo ""
echo "======================================"
echo "  배포 정보"
echo "======================================"
echo ""
echo "EC2 Instance: $INSTANCE_ID"
echo "Deploy Path: $DEPLOY_PATH"
echo "Git Repo: $GIT_REPO"
echo ""
echo "======================================"
echo "  첫 배포 시 설정"
echo "======================================"
echo ""
echo "1. EC2 접속:"
echo "   aws ssm start-session --target $INSTANCE_ID --region $AWS_REGION"
echo ""
echo "2. .env 파일 생성:"
echo "   cd $DEPLOY_PATH && sudo nano .env"
echo ""
echo "3. 컨테이너 재시작:"
echo "   cd $DEPLOY_PATH && sudo docker compose up -d"
echo ""
echo "======================================"
echo "  서비스 관리"
echo "======================================"
echo ""
echo "Docker 명령어 (EC2에서):"
echo "  cd $DEPLOY_PATH"
echo "  sudo docker compose ps           # 상태 확인"
echo "  sudo docker compose logs -f bot  # 로그 보기"
echo "  sudo docker compose restart      # 재시작"
echo "  sudo docker compose down         # 중지"
echo ""
