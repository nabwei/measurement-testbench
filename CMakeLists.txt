cmake_minimum_required(VERSION 3.24)
project(measurement_testbench LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(device_protocol src/protocol.cpp)
target_include_directories(device_protocol PUBLIC include)
if(MSVC)
    target_compile_options(device_protocol PRIVATE /W4)
else()
    target_compile_options(device_protocol PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(sensor_sim src/simulator.cpp)
target_link_libraries(sensor_sim PRIVATE device_protocol)
set_target_properties(sensor_sim PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin"
)

include(CTest)
if(BUILD_TESTING)
    include(FetchContent)
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
    set(BUILD_GMOCK OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG v1.17.0
        GIT_SHALLOW TRUE
    )
    FetchContent_MakeAvailable(googletest)
    add_executable(protocol_tests tests/cpp/test_protocol.cpp)
    target_link_libraries(protocol_tests PRIVATE device_protocol GTest::gtest_main)
    include(GoogleTest)
    gtest_discover_tests(protocol_tests NO_PRETTY_VALUES)
endif()
