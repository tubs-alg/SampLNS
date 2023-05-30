# conan v2
from conan import ConanFile
from conan.tools.files import download, copy
from conan.tools.cmake import CMake, CMakeToolchain
from conan.errors import ConanInvalidConfiguration

import sys, os, subprocess, json, tempfile, shutil, gzip


class GurobiConan(ConanFile):
    # build the current version
    version = "10.0.0"

    # the name can be set in the data file as well
    name = "gurobi"

    # we don't really have any options
    options = {}
    default_options = {}

    # URL / Homepage
    url = "https://gitlab.ibr.cs.tu-bs.de/conan-repository"
    homepage = "https://www.gurobi.com/"

    description = """
    A simple conan package to avoid trouble when setting up and using gurobi from C++.
    Should make using gurobi from C++ about as easy as with python.
    """

    author = "Phillip Keldenich"

    license = "Gurobi"

    # settings that affect the ABI
    settings = "os", "compiler", "build_type", "arch"

    def export(self):
        copy(self, 'unix10/*', self.recipe_folder, self.export_folder)
        copy(self, 'win10/*', self.recipe_folder, self.export_folder)

    def export_sources(self):
        copy(self, 'unix10/*', self.recipe_folder, self.export_sources_folder)
        copy(self, 'win10/*', self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        pass

    # try to avoid pulling in an extra copy of cmake if the system already has one
    def build_requirements(self):
        try:
            subprocess.run(["cmake", "--help"], text=True, capture_output=True,
                           check=True)
        except Exception:
            self.tool_requires("cmake/[>=3.16]")

    # configuring (option fine tuning)
    def configure(self):
        pass

    # generators to generate cmake input files
    # (toolchain and config files for dependencies)
    generators = "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def _get_config_entry(self):
        target_os = str(self.settings.os)
        target_arch = str(self.settings.arch)
        target_version = self.version
        cdata = self.conan_data["version_info"]
        if target_version not in cdata:
            raise ConanInvalidConfiguration(
                f"Unknown or unsupported version {target_version}")
        cdata = cdata[target_version]
        if target_os not in cdata:
            raise ConanInvalidConfiguration(
                f"Unknown or unsupported operating system {target_os} for version {target_version}")
        cdata = cdata[target_os]
        if target_arch not in cdata:
            raise ConanInvalidConfiguration(
                f"Unknown or unsupported architecture for OS {target_os} and version {target_version}")
        return cdata[target_arch]

    def _verify_tarfile(self, tarfile):
        for member in tarfile.getmembers():
            name = member.name
            if not member.isfile() and not member.isdir() and not member.issym():
                raise ConanInvalidConfiguration(
                    f"Downloaded tarball contains suspicious file {name}!")
            if "../" in name or "/.." in name or "\0" in name or name.startswith('/'):
                raise ConanInvalidConfiguration(
                    f"Downloaded tarball contains suspicious file {name}!")

    def _copy_file(self, relpath, extraction_location, target_location):
        source_file = os.path.join(extraction_location, relpath)
        if not os.path.isfile(source_file):
            raise ConanInvalidConfiguration(
                f"Missing expected file {relpath} after extracting archive!")
        target_name = os.path.basename(relpath)
        os.makedirs(target_location, exist_ok=True)
        target_path = os.path.join(target_location, target_name)
        shutil.copy(source_file, target_path)
        return target_path

    def _copy_directory(self, relpath, extraction_location, target_location):
        source_dir = os.path.join(extraction_location, relpath)
        if not os.path.isdir(source_dir):
            raise RuntimeError(
                f"Missing expected directory {relpath} after extracting archive!")
        if os.path.isdir(target_location):
            shutil.rmtree(target_location)
        shutil.copytree(source_dir, target_location)

    def _extract_pkg(self, config, archive):
        with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
            subprocess.run(["xar", "-xf", archive], text=True, check=True,
                           capture_output=True, cwd=tmp)
            for result_file in os.listdir(tmp):
                result_path = os.path.join(tmp, result_file)
                payload_path = os.path.join(result_path, "Payload")
                if os.path.isdir(result_path) and os.path.isfile(payload_path):
                    with gzip.open(payload_path, 'rb') as f_in:
                        payload_extract_dir = os.path.join(tmp, "extracted_payload")
                        os.mkdir(payload_extract_dir)
                        subprocess.run(["cpio", "-i"], text=False, stdin=f_in,
                                       cwd=payload_extract_dir, check=True,
                                       capture_output=True)
                    for path in config["binary_paths"]:
                        output_file = self._copy_file(path, payload_extract_dir,
                                                      "binaries")
                    for entry in config["cpp_source_dirs"]:
                        self._copy_directory(entry["path"], payload_extract_dir,
                                             entry["extract_to"])
                    return output_file
        raise ConanInvalidConfiguration(
            "Downloaded package does not contain expected payload!")

    def _extract_tar(self, config, archive):
        import tarfile
        with tarfile.open(archive, "r:*") as tar:
            self._verify_tarfile(tar)
            with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
                tar.extractall(tmp)
                for path in config["binary_paths"]:
                    output_file = self._copy_file(path, tmp, "binaries")
                for entry in config["cpp_source_dirs"]:
                    self._copy_directory(entry["path"], tmp, entry["extract_to"])
                return output_file

    def _extract_msi(self, config, archive):
        with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
            subprocess.run(["msiexec", "/a", archive, "/qn", f"TARGETDIR={tmp}"],
                           check=True, capture_output=True)
            results = [self._copy_file(path, tmp, "binaries") for path in
                       config["binary_paths"]]
            for entry in config["cpp_source_dirs"]:
                self._copy_directory(entry["path"], tmp, entry["extract_to"])
            return results

    def _download_and_extract(self):
        config_entry = self._get_config_entry()
        download_url = config_entry["download_url"]
        download_type = config_entry["download_type"]
        cmakelists = config_entry["cpp_build_cmakelists"]
        archive_file = os.path.abspath(f"./gurobi_archive.{download_type}")
        download(self, download_url, archive_file)
        if download_type.startswith("tar"):
            result = self._extract_tar(config_entry, archive_file)
        elif download_type == 'pkg':
            result = self._extract_pkg(config_entry, archive_file)
        elif download_type == 'msi':
            result = self._extract_msi(config_entry, archive_file)
        else:
            raise ConanInvalidConfiguration("Unknown or unsupported download type!")
        if "fix_binary_commands" in config_entry:
            for cmd in config_entry["fix_binary_commands"]:
                subprocess.run([*cmd, result], capture_output=True, check=True, text=True)
        if os.path.exists("CMakeLists.txt"):
            os.remove("CMakeLists.txt")
        shutil.copy(cmakelists, "CMakeLists.txt")
        return result

    def generate(self):
        c_lib_location = self._download_and_extract()
        tc = CMakeToolchain(self)
        if isinstance(c_lib_location, str):
            tc.variables["GUROBI_C_SHARED_LIB_LOCATION"] = c_lib_location.replace('\\',
                                                                                  '/')
        else:
            for i, location in enumerate(c_lib_location):
                tc.variables[f"GUROBI_C_SHARED_LIB_LOCATION{i}"] = location.replace('\\',
                                                                                    '/')
        tc.generate()

    # option fine tuning
    def config_options(self):
        pass

    # shared code between package and build (running cmake)
    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure()
        return cmake

    # define this method so we can build with conan driving cmake
    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    # define this method to create a package using conan,
    # driven by CMake's install step
    def package(self):
        cmake = self._configure_cmake()
        cmake.install()

    def package_info(self):
        config_entry = self._get_config_entry()
        self.cpp_info.libs = config_entry["library_names"]
        self.env_info.path.append(os.path.join(self.package_folder, "bin"))
