from setuptools import setup
try:
    from collections.abc import defaultdict
except ImportError:
    from collections import defaultdict
import os

__version__ = None
exec(open("spinnaker_graph_front_end/_version.py").read())
assert __version__

# Build a list of all project modules, as well as supplementary files
main_package = "spinnaker_graph_front_end"
extensions = {".aplx", ".boot", ".cfg", ".json", ".sql", ".template", ".xml",
              ".xsd"}
main_package_dir = os.path.join(os.path.dirname(__file__), main_package)
start = len(main_package_dir)
packages = []
package_data = defaultdict(list)
for dirname, dirnames, filenames in os.walk(main_package_dir):
    if '__init__.py' in filenames:
        package = "{}{}".format(
            main_package, dirname[start:].replace(os.sep, '.'))
        packages.append(package)
    for filename in filenames:
        _, ext = os.path.splitext(filename)
        if ext in extensions:
            package = "{}{}".format(
                main_package, dirname[start:].replace(os.sep, '.'))
            package_data[package].append(filename)

setup(
    name="SpiNNakerGraphFrontEnd",
    version=__version__,
    description="Front end to the SpiNNaker tool chain which uses a "
                "basic graph",
    url="https://github.com/SpiNNakerManchester/SpiNNakerGraphFrontEnd",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",

        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",

        "Natural Language :: English",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=packages,
    package_data=package_data,
    install_requires=['SpiNNUtilities >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNStorageHandlers >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNMachine >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNMan >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNaker_PACMAN >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNaker_DataSpecification >= 1!4.0.1, < 1!5.0.0',
                      'SpiNNFrontEndCommon >= 1!4.0.1, < 1!5.0.0',
                      'lxml'],
    maintainer="SpiNNakerTeam",
    maintainer_email="spinnakerusers@googlegroups.com"
)
