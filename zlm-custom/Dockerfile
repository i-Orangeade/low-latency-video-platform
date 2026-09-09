FROM ubuntu:24.04 AS build

ARG ZLM_COMMIT=da9b2017fbdd1738da4d68ff442b5eca3542c3ba
ARG BUILD_TYPE=Release

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        git \
        libssl-dev \
        wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/media
RUN git init ZLMediaKit \
    && cd ZLMediaKit \
    && git remote add origin https://github.com/ZLMediaKit/ZLMediaKit.git \
    && git fetch --depth 1 origin "${ZLM_COMMIT}" \
    && git checkout --detach FETCH_HEAD \
    && git submodule update --init --recursive --depth 1

COPY patches/ /tmp/zlm-patches/
RUN cd /opt/media/ZLMediaKit \
    && git apply --check /tmp/zlm-patches/*.patch \
    && git apply /tmp/zlm-patches/*.patch

# ZLMediaKit's WebRTC build expects libsrtp in 3rdpart/libsrtp.
RUN cd /opt/media/ZLMediaKit/3rdpart \
    && wget -q https://github.com/cisco/libsrtp/archive/v2.3.0.tar.gz -O libsrtp.tar.gz \
    && tar xzf libsrtp.tar.gz \
    && mv libsrtp-2.3.0 libsrtp \
    && cd libsrtp \
    && CFLAGS="-fcommon" ./configure --enable-openssl \
    && make -j"$(nproc)" \
    && make install

RUN cmake -S /opt/media/ZLMediaKit -B /opt/media/ZLMediaKit/build \
        -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
        -DENABLE_WEBRTC=ON \
        -DENABLE_TESTS=OFF \
        -DENABLE_API=OFF \
    && cmake --build /opt/media/ZLMediaKit/build -j"$(nproc)"

FROM ubuntu:24.04 AS runtime

ARG BUILD_TYPE=Release
ARG ZLM_COMMIT=da9b2017fbdd1738da4d68ff442b5eca3542c3ba

LABEL org.opencontainers.image.title="drone-stream-platform-zlm"
LABEL org.opencontainers.image.description="Pinned ZLMediaKit with per-stream QoS API"
LABEL org.opencontainers.image.revision="${ZLM_COMMIT}"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
           ffmpeg \
        libssl3t64 \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/media/bin
RUN mkdir -p /opt/media/conf /opt/media/bin/www

COPY --from=build /opt/media/ZLMediaKit/release/linux/${BUILD_TYPE}/MediaServer /opt/media/bin/MediaServer
COPY --from=build /opt/media/ZLMediaKit/default.pem /opt/media/bin/default.pem
COPY --from=build /opt/media/ZLMediaKit/release/linux/${BUILD_TYPE}/config.ini /opt/media/conf/config.ini
COPY --from=build /opt/media/ZLMediaKit/www/ /opt/media/bin/www/
COPY entrypoint.sh /opt/media/bin/zlm-entrypoint.sh

RUN chmod +x /opt/media/bin/zlm-entrypoint.sh

EXPOSE 80/tcp 443/tcp 554/tcp 1935/tcp 8001/tcp 8001/udp 9000/udp 10000/tcp 10000/udp

ENTRYPOINT ["/opt/media/bin/zlm-entrypoint.sh"]
