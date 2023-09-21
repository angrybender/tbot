FROM python:3.10.12-slim
WORKDIR /app/
COPY docker/src/app_nlu/requirements.txt requirements.txt
RUN apt update -y && apt install git curl -y
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install -r requirements.txt \
    && echo "Europe/Moscow" >  /etc/timezone \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8