# This is the root file for CMake, which is used to define the native part
# of the project. It is completely independent of the Python-part and can
# actually be used just to build a C++-library.
cmake_minimum_required(VERSION 3.17)  # 3.17 has been released March 2020

project(samplns CXX)  # Feel free to add more project information
set(CMAKE_CXX_STANDARD 17)  # Using C++-17 (most features with good support at 2022)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)  # The code needs to be compiled as PIC to build the shared lib for python.

if (${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
endif()

include(./cmake/CCache.cmake)  # Magic to speed up compiling by caching.

#~~~~~~~~~~~~~~~~~~~ CPM Dependencies ~~~~~~~~~~~~~~~~
# CPM allows us to include some simple dependencies without much fuss.
# Great default, for everything more complicated, uses conan.
# Why not always use conan? CPM works without any interaction (conan needs
# to be called externally). CPM also has no problems with install PyBind11
# (which conan has at the time).
# If the dependency has complicated dependencies on its own or is slow to
# compile, better use conan.
# Check out https://github.com/cpm-cmake/CPM.cmake
include(./cmake/CPM.cmake)  # Package manager for simple requirements.

CPMAddPackage("gh:fmtlib/fmt#9.1.0")  # fmt for nice strings
# further CPM-dependencies are defined in the subdirectories

#~~~~~~~~~~~~~~~~~ Conan dependencies ~~~~~~~~~~~~~~~~~~~~~
# Run `conan install . --build=missing` to create `conan_toolchain.cmake` and install
# dependencies. Add `-DCMAKE_TOOLCHAIN_FILE='./conan_toolchain.cmake'` to your cmake call
# to use this toolchain.
# The dependencies are defined in `./conanfile.txt`.
find_package(nlohmann_json REQUIRED)
find_package(gurobi REQUIRED)
find_package(fmt REQUIRED)
include_directories(${GUROBI_INCLUDE_DIRS})

#~~~~~~~~~~~~~~~~~~~ C++-Library ~~~~~~~~~~~~~~~~~~~~~~~~~
# This part defines the actual C++-library that may be used as a simple
# C++-library. The Python-interface to this library is defined separately.
add_subdirectory(src)

#~~~~~~~~~~~ TESTS OF THE PUBLIC INTERFACE ~~~~~~~~~~~~~~
# A good programmer will add at least some unit tests.
# The tests-folder can also be used for Python-tests, without interference.
if (NOT SKBUILD)
    # only import if exists. The production code may be shipped without.
    add_subdirectory(tests)  # defined in a separate CMakeLists.txt
endif ()

#~~~~~~~~~~~~~~~~~~ Python Interface ~~~~~~~~~~~~~~~~~~~~
# The Python-bindings are compiled as separate target to allow the independent
# usage of the C++-library.
add_subdirectory(pysrc)  # defined in a separate CMakeLists.txt

#~~~~~~~~~~~~~~~~ Apps ~~~~~~~~~~~~~~~~~~~~~~~~~~~
if (NOT SKBUILD)  # only make available if not using SKBUILD.
    # define your apps here
endif ()
