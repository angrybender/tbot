FROM python:3.8.16-slim-buster
COPY docker/src/app/requirements.txt requirements.txt
RUN pip install torch==1.9.1+cpu torchvision==0.10.1+cpu torchaudio==0.9.1 -f https://download.pytorch.org/whl/torch_stable.html \
    && pip install -r requirements.txt \
    && echo "Europe/Moscow" >  /etc/timezone \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8
