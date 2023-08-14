FROM python:3.10.12-slim
COPY docker/src/app/requirements.txt requirements.txt
COPY docker/src/app/post_install.sh /tmp/post_install.sh
RUN apt update -y && apt install git curl -y \
    && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt \
    && chmod +x /tmp/post_install.sh && /tmp/post_install.sh \
    && echo "Europe/Moscow" >  /etc/timezone \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8
