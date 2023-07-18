cpmaddpackage("gh:pybind/pybind11@2.10.0") # pybind11, essential

# Repeat the following part for every binding-module you want to build. If the
# different bindings need to interact with each other/share data, it may be
# easier (and cheaper) to have just a single binding. A single binding define as
# many classes and functions as you want.
# ~~~
# Create a new Python-module ~~~~~~~~~~~~~~~~~~~~~
pybind11_add_module(
  _verify # target name with leading `_` as this will be a protected
                # module.
  _verify.cpp) # the file with the API.
# enable compilation warnings
target_compile_options(
    _verify PRIVATE "$<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall>")
# This definition is important for skbuild to copy the binary to the right
# position in the package. !!! This part is critical and a wrong configuration
# leads to bad packages !!! without an error. Use a path relative to the project
# root (or !!! `cmake_install_dir`[setup.py], if used).
install(TARGETS _verify DESTINATION ./pysrc/samplns/verify/)
