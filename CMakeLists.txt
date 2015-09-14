cmake_minimum_required(VERSION 2.8.11)
# Name of the project
set(PROJECT_NAME PointBakeDemos)
project(${PROJECT_NAME})

add_subdirectory(${PROJECT_SOURCE_DIR}/PointBake/ )
add_subdirectory(${PROJECT_SOURCE_DIR}/PointBakeCloth/ )
