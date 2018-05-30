#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools
from distutils.spawn import find_executable
from conans import AutoToolsBuildEnvironment, VisualStudioBuildEnvironment
import os
import shutil

class QtConan(ConanFile):
    name = "Qt"
    version = "5.11.0"
    description = "Conan.io package for Qt library."
    url = "https://github.com/lucienboillod/conan-qt"
    license = "http://doc.qt.io/qt-5/lgpl.html"
    exports = ["LICENSE.md"]
    source_dir = "qt5"
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    submodules = [
        "qt3d",
        "qtactiveqt",
        "qtandroidextras",
        "qtcanvas3d",
        "qtcharts",
        "qtconnectivity",
        "qtdatavis3d",
        "qtdeclarative",
        "qtdoc",
        "qtgamepad",
        "qtgraphicaleffects",
        "qtimageformats",
        "qtlocation",
        "qtmacextras",
        "qtmultimedia",
        "qtnetworkauth",
        "qtpurchasing",
        "qtquickcontrols",
        "qtquickcontrols2",
        "qtscript",
        "qtscxml",
        "qtsensors",
        "qtserialbus",
        "qtserialport",
        "qtspeech",
        "qtsvg",
        "qttools",
        "qttranslations",
        "qtvirtualkeyboard",
        "qtwayland",
        "qtwebchannel",
        "qtwebengine",
        "qtwebsockets",
        "qtwebview",
        "qtwinextras",
        "qtx11extras",
        "qtxmlpatterns"]
    options = dict({
        "shared": [True, False],
        "fPIC": [True, False],
        "opengl": ["desktop", "dynamic"],
        "openssl": ["no", "yes", "linked"],
        }, **{module[2:]: [True,False] for module in submodules}
    )
    default_options = ("shared=True", "fPIC=True", "opengl=desktop", "openssl=no") + tuple(module[2:] + "=False" for module in submodules)
    short_paths = True

    def system_requirements(self):
        pack_names = None
        if tools.os_info.linux_distro == "ubuntu":
            pack_names = ["libx11-6", "libfontconfig1-dev", "libxrender-dev", "libxcursor-dev",
                          "libxext-dev", "libxfixes-dev", "libxft-dev", "libxi-dev",
                          "libgl1-mesa-dev", "libxcb1", "libxcb1-dev", "libxrandr-dev",
                          "libx11-xcb1", "libx11-xcb-dev", "libxcb-keysyms1",
                          "libxcb-keysyms1-dev", "libxcb-image0", "libxcb-image0-dev",
                          "libxcb-shm0", "libxcb-shm0-dev", "libxcb-icccm4", "libx11-dev",
                          "libxcb-icccm4-dev", "libxcb-sync1", "libxcb-sync-dev",
                          "libxcb-xfixes0-dev", "libxcb-shape0-dev", "libxcb-render-util0-dev",
                          "libxcb-randr0-dev", "libxcb-render-util0",
                          "libxcb-glx0-dev", "libxcb-xinerama0", "libxcb-xinerama0-dev"]

            if self.settings.arch == "x86":
                pack_names = [item+":i386" for item in pack_names]

        if pack_names:
            installer = tools.SystemPackageTool()
            installer.update() # Update the package database
            installer.install(" ".join(pack_names)) # Install the package

    def config_options(self):
        if self.settings.os != "Windows":
            del self.options.opengl
            del self.options.openssl

    def requirements(self):
        if self.settings.os == "Windows":
            if self.options.openssl == "yes" or self.options.openssl == "linked":
                self.requires("OpenSSL/1.0.2l@conan/stable")

    def source(self):
        url = "http://download.qt.io/official_releases/qt/{0}/{1}/single/qt-everywhere-src-{1}"\
            .format(self.version[:self.version.rfind('.')], self.version)
        if tools.os_info.is_windows:
            tools.get("%s.zip" % url)
        else:
            installer = tools.SystemPackageTool()
            installer.update() # Update the package database
            installer.install("pv")
            self.run("wget -qO- %s.tar.xz | pv | tar -xJ " % url)
        shutil.move("qt-everywhere-src-%s" % self.version, self.source_dir)

    def build(self):
        args = ["-opensource", "-confirm-license", "-nomake examples", "-nomake tests",
                "-prefix %s" % self.package_folder]
        if not self.options.shared:
            args.insert(0, "-static")
        if self.settings.build_type == "Debug":
            args.append("-debug")
        else:
            args.append("-release")
        for module in self.submodules:
            if not getattr(self.options, module[2:]):
                args.append("-skip " + module)

        if self.settings.os == "Windows":
            if self.settings.compiler == "Visual Studio":
                self._build_msvc(args)
            else:
                self._build_mingw(args)
        else:
            self._build_unix(args)

    def _build_msvc(self, args):
        build_command = find_executable("jom.exe")
        if build_command:
            build_args = ["-j", str(tools.cpu_count())]
        else:
            build_command = "nmake.exe"
            build_args = []
        self.output.info("Using '%s %s' to build" % (build_command, " ".join(build_args)))

        env = {}
        env.update({'PATH': ['%s/qtbase/bin' % self.source_folder,
                             '%s/gnuwin32/bin' % self.source_folder,
                             '%s/qtrepotools/bin' % self.source_folder]})

        env_build = VisualStudioBuildEnvironment(self)
        env.update(env_build.vars)

        with tools.environment_append(env):
            vcvars = tools.vcvars_command(self.settings)

            args += ["-opengl %s" % self.options.opengl]
            if self.options.openssl == "no":
                args += ["-no-openssl"]
            elif self.options.openssl == "yes":
                args += ["-openssl"]
            else:
                args += ["-openssl-linked"]

            self.run("cd %s && %s && set" % (self.source_dir, vcvars))
            self.run("cd %s && %s && configure %s"
                     % (self.source_dir, vcvars, " ".join(args)))
            self.run("cd %s && %s && %s %s"
                     % (self.source_dir, vcvars, build_command, " ".join(build_args)))
            self.run("cd %s && %s && %s install" % (self.source_dir, vcvars, build_command))

    def _build_mingw(self, args):
        env_build = AutoToolsBuildEnvironment(self)
        env = {'PATH': ['%s/bin' % self.source_folder,
                        '%s/qtbase/bin' % self.source_folder,
                        '%s/gnuwin32/bin' % self.source_folder,
                        '%s/qtrepotools/bin' % self.source_folder]}
        env.update(env_build.vars)
        with tools.environment_append(env):
            # Workaround for configure using clang first if in the path
            new_path = []
            for item in os.environ['PATH'].split(';'):
                if item != 'C:\\Program Files\\LLVM\\bin':
                    new_path.append(item)
            os.environ['PATH'] = ';'.join(new_path)
            # end workaround
            args += ["-opengl %s" % self.options.opengl,
                     "-platform win32-g++"]

            self.output.info("Using '%s' threads" % str(tools.cpu_count()))
            self.run("cd %s && configure.bat %s"
                     % (self.source_dir, " ".join(args)))
            self.run("cd %s && mingw32-make -j %s"
                     % (self.source_dir, str(tools.cpu_count())))
            self.run("cd %s && mingw32-make install" % (self.source_dir))

    def _build_unix(self, args):
        if self.settings.os == "Linux":
            args += ["-silent", "-xcb"]
            if self.settings.arch == "x86":
                args += ["-platform linux-g++-32"]
        else:
            args += ["-silent", "-no-framework"]
            if self.settings.arch == "x86":
                args += ["-platform macx-clang-32"]

        self.output.info("Using '%s' threads" % str(tools.cpu_count()))
        self.run("cd %s && ./configure %s" % (self.source_dir, " ".join(args)))
        self.run("cd %s && make -j %s" % (self.source_dir, str(tools.cpu_count())))
        self.run("cd %s && make install" % (self.source_dir))

    def package_info(self):
        libs = ['Concurrent', 'Core', 'DBus',
                'Gui', 'Network', 'OpenGL',
                'Sql', 'Test', 'Widgets', 'Xml']

        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        for lib in libs:
            if self.settings.os == "Windows" and self.settings.build_type == "Debug":
                suffix = "d"
            elif self.settings.os == "Macos" and self.settings.build_type == "Debug":
                suffix = "_debug"
            else:
                suffix = ""
            self.cpp_info.libs += ["Qt5%s%s" % (lib, suffix)]
            self.cpp_info.includedirs += ["include/Qt%s" % lib]

        if self.settings.os == "Windows":
            self.env_info.path.append(os.path.join(self.package_folder, "bin"))
