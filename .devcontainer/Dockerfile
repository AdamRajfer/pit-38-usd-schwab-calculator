ARG FROM_IMAGE
FROM ${FROM_IMAGE}
ARG USER
ARG USER_UID
ARG USER_GID
ARG DOCKER_GID
RUN groupadd -o --gid ${USER_GID} ${USER} \
    && useradd -l --uid ${USER_UID} --gid ${USER_GID} -d /home/${USER}-dev -m ${USER} \
    && apt-get update \
    && apt-get install bash-completion sudo \
    && echo ${USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER} \
    && chmod 0440 /etc/sudoers.d/${USER} \
    && pip install --upgrade pip
USER ${USER}
RUN pip install pre-commit \
    && curl -fsSL https://get.docker.com | sh \
    && (getent group ${DOCKER_GID} || sudo groupadd --gid ${DOCKER_GID} docker || sudo groupmod --gid ${DOCKER_GID} docker) \
    && sudo usermod -aG ${DOCKER_GID} ${USER}
