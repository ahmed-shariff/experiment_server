from pkg_resources import get_distribution, DistributionNotFound

try:
    __version__ = get_distribution('vicon_nexus_unity_stream_py').version
except DistributionNotFound:
    __version__ = '(local)'
