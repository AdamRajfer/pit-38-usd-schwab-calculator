set -e
IMAGE=$(cat .devcontainer/devcontainer.json | grep '"image":' | sed -n 's/.*: "\([^",]*\)"\{0,1\},\{0,1\}/\1/p')
FROM_IMAGE=$(echo $IMAGE | sed 's/\(.*\)---.*/\1/')
USER=$(id -un)
USER_UID=$(id -u)
USER_GID=$(id -g)
DOCKER_GID=$(getent group docker | cut -d: -f3)
echo "IMAGE: ${IMAGE}"
echo "FROM_IMAGE: ${FROM_IMAGE}"
echo "USER: ${USER}"
echo "USER_UID: ${USER_UID}"
echo "USER_GID: ${USER_GID}"
echo "DOCKER_GID: ${DOCKER_GID}"
docker build \
    -t ${IMAGE} \
    --build-arg FROM_IMAGE=${FROM_IMAGE} \
    --build-arg USER=${USER} \
    --build-arg USER_UID=${USER_UID} \
    --build-arg USER_GID=${USER_GID} \
    --build-arg DOCKER_GID=${DOCKER_GID} \
    .devcontainer
