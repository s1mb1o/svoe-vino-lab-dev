cmake_minimum_required(VERSION 3.22)
project(shelfreid CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

find_package(OpenCV REQUIRED COMPONENTS core)
if(OpenCV_VERSION_MAJOR GREATER_EQUAL 5)
  find_package(OpenCV REQUIRED COMPONENTS core imgproc features geometry video)
else()
  find_package(OpenCV REQUIRED COMPONENTS core imgproc features2d calib3d video)
endif()
# Eigen and nlohmann-json are header-only: a cross build (Android) MAY give their include
# directories instead of packages of the host.
set(EIGEN3_INCLUDE_DIR "" CACHE PATH "the Eigen headers, for a cross build")
if(EIGEN3_INCLUDE_DIR)
  add_library(Eigen3::Eigen INTERFACE IMPORTED)
  set_target_properties(Eigen3::Eigen PROPERTIES INTERFACE_INCLUDE_DIRECTORIES "${EIGEN3_INCLUDE_DIR}")
else()
  find_package(Eigen3 REQUIRED NO_MODULE)
endif()

add_library(shelfreid
  src/geometry.cpp
  src/features.cpp
  src/hungarian.cpp
  src/posegraph.cpp
  src/tracker.cpp
  src/associate.cpp
  src/realtime.cpp
  src/motion.cpp
  src/planogram.cpp)
target_include_directories(shelfreid PUBLIC include)
target_link_libraries(shelfreid PUBLIC ${OpenCV_LIBS} Eigen3::Eigen)

# The desktop tools: a replay of a video with cached detections.
option(SHELFREID_TOOLS "Build the desktop tools" ON)
if(SHELFREID_TOOLS)
  find_package(OpenCV REQUIRED COMPONENTS videoio)
  set(JSON_INCLUDE_DIR "" CACHE PATH "the nlohmann-json headers, for a cross build")
  add_executable(replay tools/replay.cpp)
  if(JSON_INCLUDE_DIR)
    target_include_directories(replay PRIVATE "${JSON_INCLUDE_DIR}")
    target_link_libraries(replay PRIVATE shelfreid opencv_videoio)
  else()
    find_package(nlohmann_json REQUIRED)
    target_link_libraries(replay PRIVATE shelfreid opencv_videoio nlohmann_json::nlohmann_json)
  endif()
endif()
