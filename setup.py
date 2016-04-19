from setuptools import setup
exec(open("spinnaker_graph_front_end/_version.py").read())

setup(
    name="spynnaker_graph_front_end",
    version=__version__,
    description="Front end to the SpiNNaker tool chain which uses a basic graph",
    url="https://github.com/SpiNNakerManchester/SpiNNakerGraphFrontEnd",
    packages=['spinnaker_graph_front_end',
              'spinnaker_graph_front_end.utilities',
              'spinnaker_graph_front_end.utilities.conf',
              'examples',
              'examples.heat_demo'],
    package_data={'examples': ['model_binaries/*.aplx'],
                  'spinnaker_graph_front_end': ['spiNNakerGraphFrontEnd.cfg'],
                  'spinnaker_graph_front_end.utilities.conf':
                      ['spiNNakerGraphFrontEnd.cfg.template']},
    install_requires=['SpiNNMachine == 2016.001',
                      'SpiNNMan == 2016.001',
                      'SpiNNaker_PACMAN == 2016.001',
                      'SpiNNaker_DataSpecification >= 2016.001',
                      'SpiNNFrontEndCommon == 2016.001',
                      'SpiNNStorageHandlers == 2016.001',
                      'numpy', 'lxml', 'six']
)
