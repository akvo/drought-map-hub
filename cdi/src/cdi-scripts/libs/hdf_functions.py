# -*- coding: utf-8 -*-
import h5py
import numpy as np


def open_dataset(file_path):
    """
    This function reads a HDF file and returns a dataset object for operations
    Args:
        file_path (str): fully-qualified path/name of the HDF file to open

    Returns:
        Scientific Dataset (SD) object
    """
    try:
        file_handler = h5py.File(file_path, 'r')
        return file_handler
    except OSError as ose:
        raise
    except Exception:
        raise


def extract_data(data_set, group, parameter, time=0):
    """
    This function extracts the data from a HDF variable as a numpy array
    Args:
        data_set (SD): class object of a read HDF file
        parameter (str): name of the parameter to extract data for
        time (int): optional index of the time array (default is 0)

    Returns:
        2D numpy array of float values
    """
    try:
        # retrieve the parameter values #
        data = data_set[group]['Data Fields'][parameter]
        results = np.array(data[:])
        # return the values #
        if time >= 0:
            return results[time]
        else:
            return results
    except IOError:
        raise
    except Exception:
        raise
