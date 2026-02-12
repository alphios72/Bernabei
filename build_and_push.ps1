docker build -t ghcr.io/alphios72/bernabei:latest -f Dockerfile .
echo "Image built successfully."
echo "Please run 'docker login ghcr.io' if the push fails."
docker push ghcr.io/alphios72/bernabei:latest
echo "Image pushed successfully."
