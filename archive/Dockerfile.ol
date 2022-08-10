# base image
FROM ubuntu
WORKDIR /usr/src/app
# update
RUN \
  echo "deb http://ports.ubuntu.com/ubuntu-ports trusty universe" >> /etc/apt/sources.list && \
  apt-get update && \
  apt-get -y upgrade

# install some basic utilities
RUN \
  apt-get install -y build-essential && \
  apt-get install -y curl git htop man unzip wget nano

# bluez dependencies
RUN \
  apt-get install -y libglib2.0-dev libical-dev libreadline-dev libudev-dev libdbus-1-dev libdbus-glib-1-dev

# debugging
RUN \
  apt-get install -y usbutils strace

# homedir
#SENV HOME /root

# workdir

COPY . .
# download, compile & install bluez
RUN wget "http://www.kernel.org/pub/linux/bluetooth/bluez-5.34.tar.xz" && \
    tar xJvf bluez-5.34.tar.xz && cd bluez-5.34 && \
    ./configure --prefix=/usr/local --disable-systemd && \
    make -j 4 && \
    make install
COPY . .
# start a shell for testing purposes
CMD ["bash"]
