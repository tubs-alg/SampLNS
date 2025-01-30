import gzip
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, download


class GurobiConan(ConanFile):
    name = "gurobi"

    def set_version(self):
        """
        Set the version from the current_version in conandata.yml.
        If the command line gives another value by
        the flag --version, that value is used instead.
        This allows using the same conanfile for multiple versions.
        """
        self.version = self.version or self.conan_data["current_version"]

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False], "fPIC": [True, False]}

    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        """
        Routine that checks which options are available,
        e.g., depending on OS, version and compiler.
        """
        if self.settings.get_safe("os") == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        """
        Routine that checks options for validity.
        If, e.g., shared builds are unavailable on Windows,
        we can raise a ConanInvalidConfiguration error here.
        """

    def requirements(self):
        """
        Method that declares our dependencies.
        """

    def build_requirements(self):
        """
        Method that declares our build requirements.
        """
        try:
            # try to avoid pulling in an extra copy of cmake if the system already has one
            subprocess.run(
                ["cmake", "--help"], text=True, capture_output=True, check=True
            )
        except Exception:
            self.tool_requires("cmake/[>=3.16]")

    def export(self):
        """
        Copy anything the conanfile.py needs to run
        to self.export_folder. Also, if there is a
        special license for just the conanfile.py,
        that should be copied here as well.
        """
        # copy(self, "conandata.yml", self.recipe_folder, self.export_folder)  # automatically exported

    def export_sources(self):
        """
        Copy sources (useful if the conanfile.py is in the same repo as the sources).
        """
        copy(
            self,
            "CMakeLists.txt",
            self.recipe_folder,
            self.export_sources_folder,
            keep_path=True,
        )

    def source(self):
        """
        This is (normally) the method to download sources.
        Unfortunately, it has to download the same
        source regardless of configuration and settings.
        This means it is useless for our purpose here:
        we have to download different archives depending on platform and architecture.
        """

    def layout(self):
        """
        Define layout.
        """
        cmake_layout(self)

    generators = "CMakeDeps", "VirtualBuildEnv", "VirtualRunEnv"

    def generate(self):
        """
        Run generators; in our case, set up the conan toolchain
        to set variables passed to CMake.
        """
        dl_result = self._download_and_extract()
        c_lib_location = dl_result["lib"]
        c_imp_location = dl_result["imp"]
        target_dir = dl_result["dir"]
        tc = CMakeToolchain(self)
        td = target_dir.replace("\\", "/")
        tc.variables["GUROBI_EXTRACT_TARGET_DIR"] = td
        tc.variables["GUROBI_C_SHARED_LIB_LOCATION"] = (
            td + "/" + c_lib_location.replace("\\", "/")
        )
        if c_imp_location:
            tc.variables["GUROBI_C_SHARED_IMP_LOCATION"] = (
                td + "/" + c_imp_location.replace("\\", "/")
            )
        if self.settings.get_safe("os") == "Windows":
            tc.variables["GUROBI_FPIC"] = "Off"
        else:
            tc.variables["GUROBI_FPIC"] = (
                "On" if self.options.get_safe("fPIC") else "Off"
            )
        tc.variables["GUROBI_VERSION"] = self.version
        tc.generate()

    def build(self):
        """
        Trigger the actual build process.
        """
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        """
        Trigger the packaging step (usually, calls CMake install)
        """
        cmake = CMake(self)
        cmake.configure()
        cmake.install()

    def package_info(self):
        """
        Export information on the provided libraries and binaries and so on.
        """
        config_entry = self._get_config_entry()
        self.cpp_info.libs = config_entry["library_names"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))

    def _get_config_entry(self):
        """
        Get the information we need for the OS, arch and version we are building for.
        """
        target_version = str(self.version)
        target_os = str(self.settings.os)
        target_arch = str(self.settings.arch)
        data = self.conan_data
        if target_version not in data["versions"]:
            msg = f"Build for unknown/unsupported version {target_version} requested"
            raise ConanInvalidConfiguration(
                msg
            )
        data = data["versions"][target_version]
        if target_os not in data:
            msg = f"Target OS {target_os} not supported for version {target_version}"
            raise ConanInvalidConfiguration(
                msg
            )
        data = data[target_os]
        if target_arch not in data:
            msg = f"Unknown or unsupported architecture {target_arch} for OS {target_os} and version {target_version}"
            raise ConanInvalidConfiguration(
                msg
            )
        return data[target_arch]

    def _verify_tarfile(self, tarfile):
        for member in tarfile.getmembers():
            name = member.name
            if not member.isfile() and not member.isdir() and not member.issym():
                msg = f"Downloaded tarball contains suspicious file {name}!"
                raise ConanInvalidConfiguration(
                    msg
                )
            if "../" in name or "/.." in name or "\0" in name or name.startswith("/"):
                msg = f"Downloaded tarball contains suspicious file {name}!"
                raise ConanInvalidConfiguration(
                    msg
                )

    def _copy_file(self, relpath, extraction_location, target_location):
        source_file = os.path.join(extraction_location, relpath)
        if not os.path.isfile(source_file):
            msg = f"Missing expected file {relpath} after extracting archive!"
            raise ConanInvalidConfiguration(
                msg
            )
        target_name = os.path.basename(relpath)
        os.makedirs(target_location, exist_ok=True)
        target_path = os.path.join(target_location, target_name)
        shutil.copy(source_file, target_path)
        return target_path

    def _copy_directory(self, relpath, extraction_location, target_location):
        source_dir = os.path.join(extraction_location, relpath)
        if not os.path.isdir(source_dir):
            msg = f"Missing expected directory {relpath} after extracting archive!"
            raise RuntimeError(
                msg
            )
        if os.path.isdir(target_location):
            shutil.rmtree(target_location)
        shutil.copytree(source_dir, target_location)

    def _extract_pkg(self, config, archive):
        """
        Extract a MacOS pkg (might only work on MacOS).
        The special cpio flag is usually only supported there.
        """
        with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
            subprocess.run(
                ["xar", "-xf", archive],
                text=True,
                check=True,
                capture_output=True,
                cwd=tmp,
            )
            for result_file in os.listdir(tmp):
                result_path = os.path.join(tmp, result_file)
                payload_path = os.path.join(result_path, "Payload")
                if os.path.isdir(result_path) and os.path.isfile(payload_path):
                    with gzip.open(payload_path, "rb") as f_in:
                        payload_extract_dir = os.path.join(tmp, "extracted_payload")
                        os.mkdir(payload_extract_dir)
                        subprocess.run(
                            ["cpio", "-i"],
                            text=False,
                            stdin=f_in,
                            cwd=payload_extract_dir,
                            check=True,
                            capture_output=True,
                        )
                    for path in config["binary_paths"]:
                        output_file = self._copy_file(
                            path, payload_extract_dir, "binaries"
                        )
                    for entry in config["cpp_source_dirs"]:
                        self._copy_directory(
                            entry["path"], payload_extract_dir, entry["extract_to"]
                        )
                    return {"lib": output_file, "imp": None, "dir": os.getcwd()}
        msg = "Downloaded package does not contain expected payload!"
        raise ConanInvalidConfiguration(
            msg
        )

    def _extract_tar(self, config, archive):
        """
        Extract a (compressed) tarball package.
        """
        import tarfile

        with tarfile.open(archive, "r:*") as tar:
            self._verify_tarfile(tar)
            with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
                tar.extractall(tmp)
                for path in config["binary_paths"]:
                    output_file = self._copy_file(path, tmp, "binaries")
                for entry in config["cpp_source_dirs"]:
                    self._copy_directory(entry["path"], tmp, entry["extract_to"])
                return {"lib": output_file, "imp": None, "dir": os.getcwd()}

    def _extract_msi(self, config, archive):
        """
        Extract a Windows MSI package (only works on Windows).
        """
        with tempfile.TemporaryDirectory(suffix="_gurobi_build") as tmp:
            subprocess.run(
                ["msiexec", "/a", archive, "/qn", f"TARGETDIR={tmp}"],
                check=True,
                capture_output=True,
            )
            results = [
                self._copy_file(path, tmp, "binaries")
                for path in config["binary_paths"]
            ]
            if len(results) != 2:
                msg = "There should be exactly two binary_paths: dll and lib (in that order)!"
                raise RuntimeError(
                    msg
                )
            for entry in config["cpp_source_dirs"]:
                self._copy_directory(entry["path"], tmp, entry["extract_to"])
            return {"lib": results[0], "imp": results[1], "dir": os.getcwd()}

    def _download_and_extract(self):
        config_entry = self._get_config_entry()
        download_url = config_entry["download_url"]
        download_type = config_entry["download_type"]
        archive_file = os.path.abspath(f"./gurobi_archive.{download_type}")
        download(self, download_url, archive_file, sha256=config_entry["sha256"])
        if download_type.startswith("tar"):
            result = self._extract_tar(config_entry, archive_file)
        elif download_type == "pkg":
            result = self._extract_pkg(config_entry, archive_file)
        elif download_type == "msi":
            result = self._extract_msi(config_entry, archive_file)
        else:
            msg = "Unknown or unsupported download type!"
            raise ConanInvalidConfiguration(msg)
        for cmd in config_entry["fix_binary_commands"]:
            subprocess.run(
                [*cmd, result["lib"]], capture_output=True, check=True, text=True
            )
        return result
