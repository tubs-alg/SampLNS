cmake_minimum_required(VERSION 3.16)
project(test_gurobi CXX)

enable_testing()
find_package(gurobi CONFIG REQUIRED)
add_executable(test_gurobi_package test.cpp)
target_link_libraries(test_gurobi_package PRIVATE gurobi::gurobi)
target_compile_features(test_gurobi_package PUBLIC cxx_std_14)
set_target_properties(test_gurobi_package PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)
add_test(NAME run_test_gurobi_package
         WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
         COMMAND test_gurobi_package)

