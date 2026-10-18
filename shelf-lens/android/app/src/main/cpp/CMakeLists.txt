cmake_minimum_required(VERSION 3.22)
project(shelfreid_app CXX)

# The core of the tracker (shelf-reid/cpp), without its desktop tools.
set(SHELFREID_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../../../../cpp shelfreid)

add_library(shelfreid_jni SHARED jni.cpp)
target_include_directories(shelfreid_jni PRIVATE ${JSON_INCLUDE_DIR})
target_link_libraries(shelfreid_jni shelfreid jnigraphics log)
