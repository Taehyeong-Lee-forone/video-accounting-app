#!/bin/bash

# 設定変数
PROJECT_ID="clean-framework-468412-v2"
SERVICE_NAME="video-accounting-app"
REGION="asia-northeast1"  # 東京リージョン
SERVICE_ACCOUNT="video-accounting-service@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Cloud Run デプロイ開始..."

# 1. gcloud設定
echo "1. プロジェクト設定..."
gcloud config set project ${PROJECT_ID}

# 2. Artifact Registryリポジトリ作成（初回のみ）
echo "2. Artifact Registry設定..."
gcloud artifacts repositories create video-accounting \
    --repository-format=docker \
    --location=${REGION} \
    --description="Video Accounting App Docker images" \
    2>/dev/null || echo "Repository already exists"

# 3. Docker認証設定
echo "3. Docker認証..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 4. バックエンドイメージビルドおよびプッシュ
echo "4. バックエンドDockerイメージビルド..."
cd backend
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/backend:latest .

echo "5. バックエンドイメージプッシュ..."
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/backend:latest

# 6. Cloud Runデプロイ
echo "6. Cloud Runサービスデプロイ..."
gcloud run deploy ${SERVICE_NAME}-backend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/backend:latest \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_API_KEY=AIzaSyDENUSgUQmX-djM2TqV9S8D58BdgSANNYw" \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GCS_BUCKET=${SERVICE_NAME}-uploads" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 100 \
    --max-instances 10

# 7. Cloud Storageバケット作成
echo "7. Cloud Storageバケット作成..."
gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${SERVICE_NAME}-uploads 2>/dev/null || echo "Bucket already exists"

# 8. フロントエンドデプロイ（Next.js）
echo "8. フロントエンドビルドおよびデプロイ..."
cd ../frontend

# Next.js Dockerfile作成
cat > Dockerfile <<EOF
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_PUBLIC_API_URL=https://${SERVICE_NAME}-backend-xxxxx.run.app
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package*.json ./
RUN npm ci --production
EXPOSE 3000
CMD ["npm", "start"]
EOF

# フロントエンドイメージビルドおよびデプロイ
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/frontend:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/frontend:latest

gcloud run deploy ${SERVICE_NAME}-frontend \
    --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/video-accounting/frontend:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1

echo "✅ デプロイ完了!"
echo "バックエンドURL: $(gcloud run services describe ${SERVICE_NAME}-backend --region ${REGION} --format 'value(status.url)')"
echo "フロントエンドURL: $(gcloud run services describe ${SERVICE_NAME}-frontend --region ${REGION} --format 'value(status.url)')"