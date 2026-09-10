#!/bin/sh
# Wait for MinIO to be healthy
echo "Waiting for MinIO to start..."
while ! curl -f http://minio:9000/minio/health/live; do
  sleep 5
done

# Set alias for MinIO using environment variables
mc alias set local http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create bucket (ignores error if it already exists)
mc mb --ignore-existing local/${MINIO_BUCKET}

# (Optional) Set the bucket download policy to public if frontend needs direct image/report access
mc anonymous set download local/${MINIO_BUCKET}

echo "MinIO bucket [${MINIO_BUCKET}] initialized successfully."
