#!/bin/bash
# Build script for Apple Silicon M-series Macs (M1/M2/M3/M4)
# With GitHub Container Registry (GHCR) support

# Text styling
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BOLD}======================================${NC}"
echo -e "${BOLD}Sleep Analysis Service - M-Series Build${NC}"
echo -e "${BOLD}======================================${NC}"

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo -e "${RED}Error: This script is designed for Apple Silicon Macs.${NC}"
    echo -e "${RED}Your architecture is $(uname -m).${NC}"
    exit 1
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in your PATH.${NC}"
    echo -e "${YELLOW}Please install Docker Desktop for Mac from https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

# Parse command line arguments
BUILD_ONLY=false
CLEAN_BUILD=false
CONTAINER_NAME="sleep-analysis-service"
TAG="apple"
PUSH_TO_GHCR=false
GITHUB_REPO=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --build-only) BUILD_ONLY=true ;;
        --clean) CLEAN_BUILD=true ;;
        --name) CONTAINER_NAME="$2"; shift ;;
        --tag) TAG="$2"; shift ;;
        --push) PUSH_TO_GHCR=true ;;
        --repo) GITHUB_REPO="$2"; shift ;;
        --help|-h)
            echo -e "${BOLD}Usage:${NC} ./m4-build.sh [OPTIONS]"
            echo -e "${BOLD}Options:${NC}"
            echo "  --build-only       Build the Docker image but don't run it"
            echo "  --clean            Force a clean build (no cache)"
            echo "  --name NAME        Set container name (default: sleep-analysis-service)"
            echo "  --tag TAG          Set image tag (default: apple)"
            echo "  --push             Push the image to GitHub Container Registry"
            echo "  --repo REPO        GitHub repository name (e.g., username/repo)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *) echo -e "${RED}Unknown parameter: $1${NC}"; exit 1 ;;
    esac
    shift
done

echo -e "${YELLOW}Building Docker image for Apple Silicon...${NC}"

# Check if Hugging Face token is set
HF_TOKEN=""
if [ -f ".env" ]; then
    source <(grep -v '^#' .env | sed -E 's/(.*)=.*/export \1/g')
    HF_TOKEN=$(grep HUGGING_FACE_HUB_TOKEN .env | cut -d '=' -f2)
fi

BUILD_ARGS=""
if [ ! -z "$HF_TOKEN" ]; then
    BUILD_ARGS="--build-arg HUGGING_FACE_HUB_TOKEN=$HF_TOKEN"
    echo -e "${GREEN}Found Hugging Face token in .env file.${NC}"
else
    echo -e "${YELLOW}No Hugging Face token found. Models requiring authentication won't be available.${NC}"
    echo -e "${YELLOW}Consider adding HUGGING_FACE_HUB_TOKEN=your_token to your .env file.${NC}"
fi

# Build the Docker image
BUILD_CMD="docker build --platform=linux/arm64 --target apple-silicon"

if [ "$CLEAN_BUILD" = true ]; then
    BUILD_CMD="$BUILD_CMD --no-cache"
    echo -e "${YELLOW}Performing clean build (no cache)${NC}"
fi

BUILD_CMD="$BUILD_CMD $BUILD_ARGS -t $CONTAINER_NAME:$TAG ."

echo -e "${YELLOW}Executing: $BUILD_CMD${NC}"
eval $BUILD_CMD

# Check if build was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Build successful!${NC}"

# Push to GitHub Container Registry if requested
if [ "$PUSH_TO_GHCR" = true ]; then
    if [ -z "$GITHUB_REPO" ]; then
        echo -e "${YELLOW}No GitHub repository specified. Trying to detect from git remote...${NC}"

        # Try to detect GitHub repository from git remote
        if command -v git &> /dev/null && git rev-parse --is-inside-work-tree &> /dev/null; then
            GITHUB_REMOTE=$(git remote get-url origin 2>/dev/null)
            if [[ $GITHUB_REMOTE == *"github.com"* ]]; then
                # Extract username/repo from different GitHub URL formats
                if [[ $GITHUB_REMOTE == https://github.com/* ]]; then
                    GITHUB_REPO=$(echo $GITHUB_REMOTE | sed 's/https:\/\/github.com\///' | sed 's/\.git$//')
                elif [[ $GITHUB_REMOTE == git@github.com:* ]]; then
                    GITHUB_REPO=$(echo $GITHUB_REMOTE | sed 's/git@github.com://' | sed 's/\.git$//')
                fi
            fi
        fi

        if [ -z "$GITHUB_REPO" ]; then
            echo -e "${RED}Error: Could not detect GitHub repository.${NC}"
            echo -e "${RED}Please specify with --repo username/repo${NC}"
            exit 1
        else
            echo -e "${GREEN}Detected GitHub repository: $GITHUB_REPO${NC}"
        fi
    fi

    # Convert all parts to lowercase for GHCR compliance
    LOWERCASE_REPO=$(echo "$GITHUB_REPO" | tr '[:upper:]' '[:lower:]')
    LOWERCASE_NAME=$(echo "$CONTAINER_NAME" | tr '[:upper:]' '[:lower:]')
    LOWERCASE_TAG=$(echo "$TAG" | tr '[:upper:]' '[:lower:]')
    GHCR_IMAGE="ghcr.io/$LOWERCASE_REPO/$LOWERCASE_NAME:$LOWERCASE_TAG"
    echo -e "${BLUE}Preparing to push to GitHub Container Registry...${NC}"
    echo -e "${YELLOW}Tagging: $CONTAINER_NAME:$TAG -> $GHCR_IMAGE${NC}"
    echo -e "${BLUE}Note: Image name converted to lowercase for GHCR compatibility${NC}"

    docker tag $CONTAINER_NAME:$TAG $GHCR_IMAGE

    echo -e "${YELLOW}Checking GitHub authentication status...${NC}"

    # Check if already logged in to GHCR
    if ! docker buildx imagetools inspect $GHCR_IMAGE &>/dev/null; then
        echo -e "${YELLOW}Please authenticate with GitHub Container Registry${NC}"
        echo -e "${YELLOW}You can use a GitHub Personal Access Token (PAT) with 'packages:read' and 'packages:write' scopes${NC}"

        # Try different login methods
        if [ -n "$GITHUB_TOKEN" ]; then
            echo -e "${GREEN}Using GITHUB_TOKEN from environment${NC}"
            echo "$GITHUB_TOKEN" | cut -c1-3 | tr -d '\n'
            echo -e "*** (token masked for security) | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin"
            echo "$GITHUB_TOKEN" | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin >/dev/null 2>&1
        else
            echo -e "${YELLOW}Login to GitHub Container Registry (ghcr.io)${NC}"
            echo -e "${YELLOW}(No output will be shown for security reasons)${NC}"
            docker login ghcr.io >/dev/null 2>&1
        fi

        if [ $? -ne 0 ]; then
            echo -e "${RED}GitHub Container Registry authentication failed!${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Already authenticated with GitHub Container Registry${NC}"
    fi

    echo -e "${BLUE}Pushing image to GitHub Container Registry...${NC}"
    docker push $GHCR_IMAGE

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to push to GitHub Container Registry!${NC}"
        exit 1
    fi

    echo -e "${GREEN}Successfully pushed to GitHub Container Registry!${NC}"
    echo -e "${GREEN}Image: $GHCR_IMAGE${NC}"
fi

# Run the container if --build-only is not set
if [ "$BUILD_ONLY" = false ]; then
    echo -e "${YELLOW}Starting container...${NC}"

    # Check if a container with the same name is already running
    if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        echo -e "${YELLOW}Container '$CONTAINER_NAME' already exists. Stopping and removing...${NC}"
        docker stop $CONTAINER_NAME >/dev/null 2>&1
        docker rm $CONTAINER_NAME >/dev/null 2>&1
    fi

    # Run the container
    docker run -d --name $CONTAINER_NAME -p 8000:8000 $CONTAINER_NAME:$TAG

    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to start container!${NC}"
        exit 1
    fi

    echo -e "${GREEN}Container started successfully!${NC}"
    echo -e "${GREEN}Service is available at http://localhost:8000${NC}"
    echo -e "${GREEN}API documentation is available at http://localhost:8000/docs${NC}"
    echo ""
    echo -e "${YELLOW}Container logs:${NC}"
    docker logs -f $CONTAINER_NAME
else
    echo -e "${GREEN}Image built successfully: $CONTAINER_NAME:$TAG${NC}"

    if [ "$PUSH_TO_GHCR" = true ]; then
        echo -e "${BLUE}GitHub Container Registry image: $GHCR_IMAGE${NC}"
        echo -e "${YELLOW}To pull this image:${NC}"
        echo -e "docker pull $GHCR_IMAGE"
    fi

    echo -e "${YELLOW}To run the container:${NC}"
    echo -e "docker run -d --name $CONTAINER_NAME -p 8000:8000 $CONTAINER_NAME:$TAG"
fi
