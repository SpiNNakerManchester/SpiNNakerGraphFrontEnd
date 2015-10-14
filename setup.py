from setuptools import setup
exec(open("spynnaker_graph_front_end/_version.py").read())

setup(
    name="spynnaker_graph_front_end",
    version=__version__,
    description="Front end to the SpiNNaker tool chain which uses a basic graph",
    url="https://github.com/SpiNNakerManchester/SpiNNakerGraphFrontEnd",
    packages=['spynnaker_graph_front_end',
              'spynnaker_graph_front_end.models',
              'spynnaker_graph_front_end.utilities',
              'spynnaker_graph_front_end.utilities.conf',
              'examples',
              'examples.heat_demo'],
    package_data={'examples': ['model_binaries/*.aplx'],
                  'spynnaker_graph_front_end': ['spiNNakerGraphFrontEnd.cfg'],
                  'spynnaker_graph_front_end.utilities.conf':
                      ['spiNNakerGraphFrontEnd.cfg.template']},
    install_requires=['SpiNNMachine >= 2015.003-alpha-01',
                      'SpiNNMan >= 2015.003-alpha-01',
                      'SpiNNaker_PACMAN >= 2015.003-alpha-02',
                      'SpiNNaker_DataSpecification >= 2015.003-alpha-01',
                      'SpiNNFrontEndCommon >= 2015.001-alpha-01',
                      'numpy', 'lxml', 'six']
)
