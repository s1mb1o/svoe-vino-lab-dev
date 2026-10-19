cmake_minimum_required(VERSION 3.22)
project(shelfreid_app CXX)

# The core of the tracker (shelf-reid/cpp), without its desktop tools.
set(SHELFREID_TOOLS OFF CACHE BOOL "" FORCE)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../../../../cpp shelfreid)

# ONNX Runtime for the bottle detector: headers and the library to link against from the
# unpacked onnxruntime-android package (ORT_ANDROID_DIR); the APK gets the same library from
# its Maven dependency.
add_library(onnxruntime SHARED IMPORTED)
set_target_properties(onnxruntime PROPERTIES IMPORTED_LOCATION ${ORT_ANDROID_DIR}/jni/${ANDROID_ABI}/libonnxruntime.so)

add_library(shelfreid_jni SHARED jni.cpp detector.cpp pipeline.cpp)
target_include_directories(shelfreid_jni PRIVATE ${JSON_INCLUDE_DIR} ${ORT_ANDROID_DIR}/headers)
target_link_libraries(shelfreid_jni shelfreid onnxruntime jnigraphics log)
