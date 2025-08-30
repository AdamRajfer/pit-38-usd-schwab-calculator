ARG FROM_IMAGE
FROM ${FROM_IMAGE}
ARG USER
ARG USER_UID
ARG USER_GID
RUN groupadd -o --gid ${USER_GID} ${USER} \
    && useradd -l --uid ${USER_UID} --gid ${USER_GID} -d /home/${USER}-dev -m ${USER} \
    && apt-get update \
    && apt-get install -y bash-completion sudo \
    && echo ${USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER} \
    && chmod 0440 /etc/sudoers.d/${USER} \
    && pip install --upgrade pip \
    && sudo usermod -s /bin/bash ${USER}
USER ${USER}
ENV PATH=${PATH}:/home/${USER}-dev/.local/bin
