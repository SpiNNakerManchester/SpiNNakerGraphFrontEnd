from setuptools import setup
exec(open("spinnaker_graph_front_end/_version.py").read())

setup(
    name="SpiNNakerGraphFrontEnd",
    version=__version__,
    description="Front end to the SpiNNaker tool chain which uses a basic graph",
    url="https://github.com/SpiNNakerManchester/SpiNNakerGraphFrontEnd",
    packages=['spinnaker_graph_front_end',
              'spinnaker_graph_front_end.utilities',
              'spinnaker_graph_front_end.utilities.conf',
              'spinnaker_graph_front_end.examples',
              'spinnaker_graph_front_end.examples.heat_demo',
              'spinnaker_graph_front_end.examples.hello_world'],
    package_data={'spinnaker_graph_front_end.examples.heat_demo': ['*.aplx'],
                  'spinnaker_graph_front_end.examples.hello_world': ['*.aplx'],
                  'spinnaker_graph_front_end': ['spiNNakerGraphFrontEnd.cfg'],
                  'spinnaker_graph_front_end.utilities.conf':
                      ['spiNNakerGraphFrontEnd.cfg.template']},
    install_requires=['SpiNNMachine == 2016.001',
                      'SpiNNMan == 2016.001',
                      'SpiNNaker_PACMAN == 2016.001',
                      'SpiNNaker_DataSpecification == 2016.001',
                      'SpiNNFrontEndCommon == 2016.001',
                      'SpiNNStorageHandlers == 2016.001',
                      'numpy', 'lxml', 'six']
)
