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
find_package(Eigen3 REQUIRED NO_MODULE)

add_library(shelfreid
  src/geometry.cpp
  src/features.cpp
  src/hungarian.cpp
  src/posegraph.cpp
  src/tracker.cpp
  src/associate.cpp
  src/realtime.cpp)
target_include_directories(shelfreid PUBLIC include)
target_link_libraries(shelfreid PUBLIC ${OpenCV_LIBS} Eigen3::Eigen)

# The desktop tools: a replay of a video with cached detections.
option(SHELFREID_TOOLS "Build the desktop tools" ON)
if(SHELFREID_TOOLS)
  find_package(OpenCV REQUIRED COMPONENTS videoio)
  find_package(nlohmann_json REQUIRED)
  add_executable(replay tools/replay.cpp)
  target_link_libraries(replay PRIVATE shelfreid opencv_videoio nlohmann_json::nlohmann_json)
endif()
