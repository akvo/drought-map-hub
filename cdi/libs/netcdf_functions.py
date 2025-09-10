# -*- coding: utf-8 -*-
from netCDF4 import Dataset
import numpy as np
from datetime import datetime


def open_dataset(file_path, action='r'):
    """
    This function open a NetCDF file and returns a Dataset object with the appropriate operation:
        read, write, or append
    Args:
        file_path (str): fully-qualified path/name of the NetCDF file
        action (str): optional action flag for the dataset operation: r (default), w, a

    Returns:
        NetCDF4 Dataset object
    """
    try:
        return Dataset(r'{}'.format(file_path), action)
    except IOError:
        raise
    except Exception:
        raise


def get_dimensions(data_set):
    """
    This function reads the latitude and longitude dimensions from a specified NetCDF file
    Args:
        data_set (NetCDF4): class object of a read NetCDF file

    Returns:
        latitudes: List of latitude values as floats
        longitudes: List of longitude values as floats
    """
    results = {
        'latitudes': [],
        'longitudes': [],
        'times': [],
        'time units': ''
    }
    try:
        # get list of dimensions #
        dimension_names = data_set.dimensions
        # search the dimension names for matches to latitude/longitude possibilities #
        for name in dimension_names:
            # determine dimension name for latitude
            if str(name).lower() in ['y', 'lat', 'latitudes']:
                # retrieve the latitude array #
                results['latitudes'] = np.round(np.array(data_set.variables[name]), 3)
            # determine dimension name for longitude
            if str(name).lower() in ['x', 'lon', 'longitudes']:
                # retrieve the longitude array #
                results['longitudes'] = np.round(np.array(data_set.variables[name]), 3)
        # retrieve the time array #
        if 'time' in dimension_names:
            results['times'] = np.array(data_set.variables['time'])
            results['time units'] = data_set.variables['time'].units
        # return the dimension values #
        return results
    except IOError:
        raise
    except Exception:
        raise


def extract_data(data_set, parameter, time=0):
    """
    This function extracts the data from a NetCDF variable as a numpy array
    Args:
        data_set (NetCDF4): class object of a read NetCDF file
        parameter (str): name of the parameter to extract data for
        time (int): optional index of the time array (default is 0)

    Returns:
        2D/3D numpy array of float values
    """
    try:
        # retrieve the parameter values #
        if time >= 0:  # just the single time position
            return np.array(data_set.variables[parameter][time]).astype(float)
        else:  # all times (or just the data if no time dimension)
            return np.array(data_set.variables[parameter]).astype(float)
    except IOError:
        raise
    except Exception:
        raise


def extract_data_range(data_set, parameter, start, stop):
    """
    This function extracts the data from a NetCDF variable across a given time range as a numpy array
    Args:
        data_set (NetCDF4): class object of a read NetCDF file
        parameter (str): name of the parameter to extract data for
        start (int): the first index of the data range
        stop (int): the last index of the data range

    Returns:
        3D numpy array of float values
    """
    try:
        # create the output array #
        times, lats, lons = data_set.variables[parameter].shape
        # retrieve the parameter values #
        data = np.empty([(stop-start), lats, lons])
        print(data.shape, data_set.variables[parameter].shape)
        for t in range(start, stop):
            data[t] = np.array(data_set.variables[parameter][t])
        return data
    except ValueError:
        raise
    except IOError:
        raise
    except Exception:
        raise


def get_parameter_units(data_set, parameter):
    """

    Args:
        data_set (NetCDF4): class object of a read NetCDF file
        parameter (str): name of the parameter to extract data for

    Returns:
        string of the parameter units
    """
    try:
        # retrieve the parameter values #
        results = data_set.variables[parameter].units
        # return the values #
        return results
    except IOError:
        raise
    except Exception:
        raise


def initialize_dataset(file_path, properties):
    data_set = None
    try:
        data_set = Dataset(file_path, 'w', 'NETCDF4')

        today = datetime.today()
        data_set.history = "Created " + today.strftime("%d/%m/%y")

        # retrieve properties #
        latitudes = properties['latitudes']
        longitudes = properties['longitudes']
        times = properties['times']
        time_units = properties['time_units']

        # create dimensions #
        data_set.createDimension('latitude', len(latitudes))
        data_set.createDimension('longitude', len(longitudes))
        data_set.createDimension('time', len(times))

        # populate dimension variables #
        # latitude #
        lat_var = data_set.createVariable('latitude', 'float64', 'latitude')
        lat_var[:] = latitudes
        lat_var.standard_name = 'latitude'
        lat_var.long_name = 'latitude'
        lat_var.axis = 'latitude'
        lat_var.units = 'degrees_north'
        # longitude #
        lon_var = data_set.createVariable('longitude', 'float64', 'longitude')
        lon_var[:] = longitudes
        lon_var.standard_name = 'longitude'
        lon_var.long_name = 'longitude'
        lon_var.axis = 'longitude'
        lon_var.units = 'degrees_east'
        # time #                 
        time_var = data_set.createVariable('time', 'float64', 'time')
        time_var.units = time_units
        time_var.calendar = "proleptic_gregorian"
        time_var.standard_name = 'time'
        time_var[:] = times

        # global attributes ###
        data_set.MAP_PROJECTION = "EPSG:4326"
        data_set.SOUTH_WEST_CORNER_LAT = np.float32(latitudes[0])
        data_set.SOUTH_WEST_CORNER_LON = np.float32(longitudes[0])
        data_set.DX = np.float32(0.05)
        data_set.DY = np.float32(0.05)
        data_set.missing_value = -9999.0
        return data_set
    except IOError:
        raise
    except Exception:
        if data_set is not None:
            data_set.close()
        raise
