__author__ = 'alan'
from data_specification import constants as ds_constants

def get_region_base_address_offset(app_data_base_address, region):
    return (app_data_base_address +
            ds_constants.APP_PTR_TABLE_HEADER_BYTE_SIZE + (region * 4))