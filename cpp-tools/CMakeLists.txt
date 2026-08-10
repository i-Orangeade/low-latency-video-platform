cmake_minimum_required(VERSION 3.16)

project(drone_stream_tools LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(stream_pusher stream-pusher/main.cpp)
add_executable(latency_probe latency-probe/main.cpp)
add_executable(stream_health_agent stream-health-agent/main.cpp)
