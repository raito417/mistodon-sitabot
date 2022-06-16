FROM python:3.9.13-buster
LABEL maintainer="hogeika2@gmail.com"
LABEL version="1.0"

WORKDIR /work
COPY requirements.txt /work
RUN pip3 install -r requirements.txt

RUN apt-get update && apt-get install -y \
    software-properties-common

CMD ["/bin/bash"]