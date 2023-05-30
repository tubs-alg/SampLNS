cmake_minimum_required(VERSION 3.16)
project(gurobi CXX)
include(GNUInstallDirs)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_EXTENSIONS Off)

if(NOT DEFINED GUROBI_C_SHARED_LIB_LOCATION0 OR NOT DEFINED GUROBI_C_SHARED_LIB_LOCATION1)
	message(FATAL_ERROR "This CMake script expects the location of the gurobi import library (GUROBI_C_SHARED_LIB_LOCATION0) annd dll (GUROBI_C_SHARED_LIB_LOCATION1) to be specified!")
endif()

if(NOT EXISTS "${GUROBI_C_SHARED_LIB_LOCATION0}" OR NOT EXISTS "${GUROBI_C_SHARED_LIB_LOCATION1}")
	message(FATAL_ERROR "The path '${GUROBI_C_SHARED_LIB_LOCATION0}' given as GUROBI_C_SHARED_LIB_LOCATION0 does not point to an existing file!")
endif()

add_library(__gurobi_clib IMPORTED SHARED)
set_target_properties(__gurobi_clib PROPERTIES IMPORTED_LOCATION "${GUROBI_C_SHARED_LIB_LOCATION0}"
                                               IMPORTED_IMPLIB "${GUROBI_C_SHARED_LIB_LOCATION1}")
add_executable(__gurobi_grbgetkey IMPORTED)
set_target_properties(__gurobi_grbgetkey PROPERTIES IMPORTED_LOCATION "${CMAKE_CURRENT_LIST_DIR}/bin/grbgetkey.exe")
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
list(TRANSFORM cpp_sources PREPEND "src/")
add_library(gurobi_c++ STATIC ${cpp_sources})
set_target_properties(gurobi_c++ PROPERTIES POSITION_INDEPENDENT_CODE On
                                            CXX_VISIBILITY_PRESET hidden
                                            CXX_VISIBILITY_INLINES_HIDDEN On)
target_include_directories(gurobi_c++ PUBLIC 
	$<BUILD_INTERFACE:${CMAKE_CURRENT_LIST_DIR}/${GUROBI_VERSION}/include> # include the public header directory in the source tree when building the lib
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)                      # include the include directory when using the installed lib

set(_GUROBI_PUBHEADERS "${CMAKE_CURRENT_LIST_DIR}/include/gurobi_c.h"
	                   "${CMAKE_CURRENT_LIST_DIR}/include/gurobi_c++.h")
set_target_properties(gurobi_c++ PROPERTIES PUBLIC_HEADER "${_GUROBI_PUBHEADERS}")
install(IMPORTED_RUNTIME_ARTIFACTS __gurobi_clib LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
                                                 RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(FILES "${GUROBI_C_SHARED_LIB_LOCATION1}" DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(IMPORTED_RUNTIME_ARTIFACTS __gurobi_grbgetkey RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}"
                                                      LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(TARGETS gurobi_c++ EXPORT gurobi_c++_targets
        PUBLIC_HEADER DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
        LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}")