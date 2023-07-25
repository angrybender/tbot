FROM python:3.10.12-slim
COPY docker/src/app/requirements.txt requirements.txt
RUN pip install -r requirements.txt \
    && echo "Europe/Moscow" >  /etc/timezone \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8
