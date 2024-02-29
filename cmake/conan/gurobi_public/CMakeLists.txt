cmake_minimum_required(VERSION 3.16)
project(gurobi CXX)
include(GNUInstallDirs)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_EXTENSIONS Off)

if(NOT DEFINED GUROBI_EXTRACT_TARGET_DIR)
  message(FATAL_ERROR "This CMake script expects the location of the extracted folders to be specified!")
endif()

if(NOT EXISTS "${GUROBI_EXTRACT_TARGET_DIR}")
  message(FATAL_ERROR "The extraction target directory ${GUROBI_EXTRACT_TARGET_DIR} does not exist!")
endif()

if(NOT DEFINED GUROBI_C_SHARED_LIB_LOCATION)
  message(FATAL_ERROR "This CMake script expects the location of the gurobi shared library (GUROBI_C_SHARED_LIB_LOCATION) to be specified!")
endif()

if(NOT EXISTS "${GUROBI_C_SHARED_LIB_LOCATION}")
  message(FATAL_ERROR "The specified shared library file '${GUROBI_C_SHARED_LIB_LOCATION}' does not exist!")
endif()

if(WIN32 AND NOT DEFINED GUROBI_C_SHARED_IMP_LOCATION)
  message(FATAL_ERROR "This CMake script expects the location of the gurobi shared libraries' import library to be specified!")
endif()

if(WIN32 AND NOT EXISTS "${GUROBI_C_SHARED_IMP_LOCATION}")
  message(FATAL_ERROR "The specified import library file '${GUROBI_C_SHARED_LIB_LOCATION}' does not exist!")
endif()

if(NOT DEFINED GUROBI_VERSION)
  message(FATAL_ERROR "This CMake scripts expects the gurobi version it builds to be specified!")
endif()

if(NOT DEFINED GUROBI_FPIC)
  message(FATAL_ERROR "This CMake script expects that an FPIC build (or not) is selected.")
endif()

add_library(__gurobi_clib IMPORTED SHARED)
set_target_properties(__gurobi_clib PROPERTIES IMPORTED_LOCATION "${GUROBI_C_SHARED_LIB_LOCATION}")
if(WIN32)
  set_target_properties(__gurobi_clib PROPERTIES IMPORTED_IMPLIB "${GUROBI_C_SHARED_IMP_LOCATION}")
  add_executable(__gurobi_grbgetkey IMPORTED)
  set_target_properties(__gurobi_grbgetkey PROPERTIES IMPORTED_LOCATION "${GUROBI_EXTRACT_TARGET_DIR}/bin/grbgetkey.exe")
else()
  add_executable(__gurobi_grbgetkey IMPORTED)
  set_target_properties(__gurobi_grbgetkey PROPERTIES IMPORTED_LOCATION "${GUROBI_EXTRACT_TARGET_DIR}/bin/grbgetkey")
endif()

set(cpp_sources
	"attrprivate.cpp"
	"Batch.cpp"
	"Callback.cpp"
	"Column.cpp"
	"Constr.cpp"
	"Env.cpp"
	"Exception.cpp"
	"GenConstr.cpp" 
	"LinExpr.cpp"
	"Model.cpp"
	"QConstr.cpp"
	"QuadExpr.cpp"
	"SOS.cpp"
	"TempConstr.cpp"
	"Var.cpp")

list(TRANSFORM cpp_sources PREPEND "${GUROBI_EXTRACT_TARGET_DIR}/src/")
add_library(gurobi_c++ STATIC ${cpp_sources})
set_target_properties(gurobi_c++ PROPERTIES POSITION_INDEPENDENT_CODE ${GUROBI_FPIC}
                                            CXX_VISIBILITY_PRESET hidden
                                            CXX_VISIBILITY_INLINES_HIDDEN On)
target_include_directories(gurobi_c++ PUBLIC 
$<BUILD_INTERFACE:${GUROBI_EXTRACT_TARGET_DIR}/include> # include the public header directory in the source tree when building the lib
$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)       # include the include directory when using the installed lib

# setup header installation
set(_GUROBI_PUBHEADERS "${GUROBI_EXTRACT_TARGET_DIR}/include/gurobi_c.h"
                       "${GUROBI_EXTRACT_TARGET_DIR}/include/gurobi_c++.h")
set_target_properties(gurobi_c++ PROPERTIES PUBLIC_HEADER "${_GUROBI_PUBHEADERS}")

if(WIN32)
  # on Windows, the runtime (dll) goes into bin, not lib
  install(IMPORTED_RUNTIME_ARTIFACTS __gurobi_clib LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
                                                   RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
  # and we have to install the import library as well (into lib)
  install(FILES "${GUROBI_C_SHARED_IMP_LOCATION}" DESTINATION "${CMAKE_INSTALL_LIBDIR}")
else()
  # on other systems, install shared library to lib
  install(IMPORTED_RUNTIME_ARTIFACTS __gurobi_clib LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
                                                   RUNTIME DESTINATION "${CMAKE_INSTALL_LIBDIR}")
endif()

# also install grbgetkey
install(IMPORTED_RUNTIME_ARTIFACTS __gurobi_grbgetkey RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
                                                      LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(TARGETS gurobi_c++ EXPORT gurobi_c++_targets
        PUBLIC_HEADER DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
        LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}")

