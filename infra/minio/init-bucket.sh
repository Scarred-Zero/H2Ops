#!/bin/sh
# Wait for MinIO to be healthy
echo "Waiting for MinIO to start..."
while ! curl -f http://minio:9000/minio/health/live; do
  sleep 1
done

# Set alias for MinIO using environment variables
mc alias set local http://minio:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadminpassword}

# Create bucket (ignores error if it already exists)
mc mb --ignore-existing local/${MINIO_BUCKET:-reports}

# Set policy to allow public read (download) access
mc anonymous set download local/${MINIO_BUCKET:-reports}

echo "MinIO bucket [${MINIO_BUCKET:-reports}] initialized successfully."