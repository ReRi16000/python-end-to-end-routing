FROM ubuntu
WORKDIR /compnets

# The following shows the hostname in prompt/title
# HOSTNAME must be set for this

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y net-tools netcat tcpdump inetutils-ping python3 wireshark

RUN setcap cap_net_raw,cap_net_admin=eip /usr/bin/dumpcap

RUN apt-get update && apt-get install -y libxkbcommon-x11-0
RUN apt-get install -y pip
RUN pip3 install numpy
RUN pip3 install psutil
COPY endpoint.py /compnets
COPY router.py /compnets
COPY constants.py /compnets
ENV DISPLAY=host.docker.internal:0
ENV LIBGL_ALWAYS_INDIRECT=1
ENV DEBIAN_FRONTEND=noninteractive
ENV XDG_RUNTIME_DIR=/tmp/foobar
CMD ["/bin/bash"]
