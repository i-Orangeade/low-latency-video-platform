cmake_minimum_required(VERSION 3.16)
project(foundation_labs LANGUAGES CXX)

option(FOUNDATION_ENABLE_ASAN "Build with AddressSanitizer and UBSan" OFF)
option(FOUNDATION_ENABLE_TSAN "Build with ThreadSanitizer" OFF)

if(FOUNDATION_ENABLE_ASAN AND FOUNDATION_ENABLE_TSAN)
  message(FATAL_ERROR "ASAN and TSAN cannot be enabled together")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_compile_options(-Wall -Wextra -Wpedantic)

if(FOUNDATION_ENABLE_ASAN)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
elseif(FOUNDATION_ENABLE_TSAN)
  add_compile_options(-fsanitize=thread -fno-omit-frame-pointer)
  add_link_options(-fsanitize=thread)
endif()

find_package(Threads REQUIRED)

add_executable(epoll_echo_server src/epoll_echo_server.cpp)
target_compile_definitions(epoll_echo_server PRIVATE _GNU_SOURCE)

add_executable(bounded_queue_demo src/bounded_queue_demo.cpp)
target_link_libraries(bounded_queue_demo PRIVATE Threads::Threads)

include(CTest)
if(BUILD_TESTING)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  add_test(
    NAME foundation_labs
    COMMAND
      ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/run_tests.py
      --echo-server $<TARGET_FILE:epoll_echo_server>
      --queue-demo $<TARGET_FILE:bounded_queue_demo>
      --analyzer ${CMAKE_CURRENT_SOURCE_DIR}/tools/media_analyzer.py
  )
  set_tests_properties(foundation_labs PROPERTIES TIMEOUT 30)
endif()
