try:
    # conan v2
    from conan import ConanFile
    from conan.tools.cmake import CMake, cmake_layout

    is_conan_v2 = True
except ImportError:
    # conan v1
    from conan.tools.cmake import CMake
    from conans import ConanFile

    is_conan_v2 = False


class GurobiTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"
    options = {}

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure()
        return cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def test(self):
        cmake = self._configure_cmake()
        cmake.test()


def _requires_method(self):
    self.requires(self.tested_reference_str)


def _layout_method(self):
    cmake_layout(self)


if is_conan_v2:
    GurobiTestPackageConan.requirements = _requires_method
    GurobiTestPackageConan.layout = _layout_method
