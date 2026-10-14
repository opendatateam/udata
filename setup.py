from babel.messages.frontend import CommandLineInterface
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyWithCatalogs(build_py):
    """Compile the gettext catalogs so any build ships the .mo files, which are not versioned."""

    def run(self):
        CommandLineInterface().run(
            ["pybabel", "compile", "-D", "udata", "-d", "udata/translations"]
        )
        super().run()


setup(cmdclass={"build_py": BuildPyWithCatalogs})
