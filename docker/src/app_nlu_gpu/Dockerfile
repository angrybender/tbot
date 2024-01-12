FROM python:3.10.12-slim
WORKDIR /app/
COPY docker/src/app_nlu/requirements.txt requirements.txt
COPY docker/src/app_nlu_gpu/cuda_12.3.1_545.23.08_linux.run /tmp/cuda_12.3.1_545.23.08_linux.run
RUN apt update -y && apt install git curl wget libxml2 -y
RUN wget  https://download.pytorch.org/whl/cu121/torch-2.1.1%2Bcu121-cp310-cp310-linux_x86_64.whl -O "/tmp/torch-2.1.1+cu121-cp310-cp310-linux_x86_64.whl"
RUN pip install "/tmp/torch-2.1.1+cu121-cp310-cp310-linux_x86_64.whl"
#RUN wget https://raw.githubusercontent.com/TimDettmers/bitsandbytes/main/cuda_install.sh
#RUN bash cuda_install.sh 123 ~/local/ 0
RUN bash /tmp/cuda_12.3.1_545.23.08_linux.run --no-drm --no-man-page --override --toolkitpath=/usr/local/cuda-12.3/ --toolkit --silent
RUN pip install transformers[torch] sentencepiece git+https://github.com/huggingface/peft.git Flask==2.3.1 scipy bitsandbytes git+https://github.com/huggingface/accelerate.git \
    && echo "Europe/Moscow" >  /etc/timezone \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/usr/local/cuda-12.3/targets/x86_64-linux/lib/