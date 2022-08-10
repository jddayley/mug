FROM python:3
WORKDIR /usr/src/app
RUN apt-get update
RUN apt-get install -y bluez bluetooth vim
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT sh docker_entrypoint.sh
