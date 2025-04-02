#!/bin/bash
# m4-build.sh

# Set parent directory path
PARENT_DIR=".."

# Load environment variables from .env file in parent directory
PARENT_ENV="$PARENT_DIR/.env"
if [ -f "$PARENT_ENV" ]; then
  echo "Loading environment variables from parent directory .env file..."
  export $(grep -v '^#' "$PARENT_ENV" | xargs)
else
  echo "Warning: No .env file found in parent directory. Make sure to set required variables manually."
fi

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN environment variable is not set."
  echo "Please add it to your .env file or set it manually."
  exit 1
fi

# Login to GitHub Container Registry
echo "Logging in to GitHub Container Registry..."
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin

if [ $? -ne 0 ]; then
  echo "Failed to log in to GitHub Container Registry."
  exit 1
fi

# Generate tag based on date and time
TAG="m4-$(date +%Y%m%d-%H%M%S)"

# Build the Docker image, using Dockerfile from parent directory
echo "Building Docker image for M4..."
docker build \
  --build-arg OPTIMIZE_FOR_M4=true \
  --build-arg HF_TOKEN=$HF_TOKEN \
  -t ghcr.io/$GITHUB_USERNAME/$REPO_NAME:$TAG \
  -t ghcr.io/$GITHUB_USERNAME/$REPO_NAME:m4-latest \
  -f $PARENT_DIR/Dockerfile \
  $PARENT_DIR

if [ $? -ne 0 ]; then
  echo "Docker build failed."
  exit 1
fi

# Push the image to GitHub Container Registry
echo "Pushing image to GitHub Container Registry..."
docker push ghcr.io/$GITHUB_USERNAME/$REPO_NAME:$TAG
docker push ghcr.io/$GITHUB_USERNAME/$REPO_NAME:m4-latest

echo "Successfully built and pushed M4-optimized image:"
echo "ghcr.io/$GITHUB_USERNAME/$REPO_NAME:$TAG"
echo "ghcr.io/$GITHUB_USERNAME/$REPO_NAME:m4-latest"
