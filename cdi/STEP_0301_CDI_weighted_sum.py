# -*- coding: utf-8 -*-
import os
import sys
from libs.config_reader import ConfigParser
import libs.netcdf_functions as netcdf
import numpy as np
import numpy.ma as ma
from datetime import datetime


class CompositeDroughtIndicator:
    """
    This is the core processing class for executing all CDI operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__cdi_weights = self.__config.get('cdi_parameters', 'weights')
        self.__parameter_names = self.__config.get('cdi_parameters', 'names')
        self.__ranking_files = {
            "lst": os.path.join(self.__output_dir, "STEP_0201_LST_anomaly_pct_rank_{}.nc".format(self.__region)),
            "ndvi": os.path.join(self.__output_dir, "STEP_0202_NDVI_anomaly_pct_rank_{}.nc".format(self.__region)),
            "spi": os.path.join(self.__output_dir, "STEP_0203_SPI_anomaly_pct_rank_{}.nc".format(self.__region)),
            "sm": os.path.join(self.__output_dir, "STEP_0204_SM_pct_rank_{}.nc".format(self.__region))
        }
        self.__cdi_inputs = []
        self.__datasets = {}
        self.__common_times = []
        self.__times = {}
        self.__last_time_index = 0
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__missing = -9999.0
        self.__rows = len(self.__latitudes)
        self.__columns = len(self.__longitudes)
        self.__empty_set = np.full((self.__rows, self.__columns), self.__missing)
        self.__check_weight_totals()
        self.__get_data_sets()

    def __check_weight_totals(self):
        """
        This function verifies the total weights set in the configuration
         and alerts the user if the total value is not 1.0
        Returns:
            None: Exits if there is invalid input
        """
        total_weight = 0
        for param in self.__cdi_weights:
            total_weight += self.__cdi_weights[param]
        if total_weight != 1.0:
            print("Total CDI weight is not equal to 1.0.\nPlease adjust the weights in the configuration to total 1.0")
            sys.exit(1)

    def __get_cdi_inputs(self):
        """
        This function loads the CDI input weights form the configuration file and adds any weights > 0.0 to the list of inputs to use
            This allows easy adjustment of the individual parameters and their weights for the CDI
        Returns:
            None: parameter strings are stored in the class
        """
        for param in self.__cdi_weights:
            weight = self.__cdi_weights[param]
            if weight > 0:
                self.__cdi_inputs.append(param)

    def __get_data_sets(self):
        """
        This function opens the appropriate input datasets for creating the CDI
        Returns:
            None: references are stored in the class
        """
        try:
            self.__get_cdi_inputs()
            for param in self.__cdi_inputs:
                self.__datasets[param] = netcdf.open_dataset(self.__ranking_files[param])
        except IOError:
            raise
        except Exception:
            raise

    def __get_time_range(self, source):
        """
        This function gets the indices from an input time dimension where the NetCDF dates match the common dates between all inputs
        Args:
            source (str): the name of the input parameter

        Returns:
            list of indices matching the common dates to use
        """
        try:
            start_idx = 0
            end_idx = 0
            date_list = self.__times[source]
            for d, date in enumerate(date_list):
                if date == self.__common_times[0]:
                    start_idx = d
                elif date == self.__common_times[self.__last_time_index]:
                    end_idx = d + 1
            return range(start_idx, end_idx)
        except ValueError:
            raise
        except Exception:
            raise

    def get_common_dates(self):
        """
        This function compares the dates of all the CDI inputs to determine what dates all inputs have in common
        Returns:
            None: values are directly stored to the class
        """
        try:
            sets = []
            # load the time arrays from the ranking files #
            for param in self.__cdi_inputs:
                self.__times[param] = netcdf.extract_data(self.__datasets[param], 'time', -1)
                sets.append(set(self.__times[param]))
            # find the common dates between the four lists #
            intersections = set.intersection(*sets)
            date_list = list(intersections)
            self.__common_times = sorted(date_list)
            self.__last_time_index = len(self.__common_times) - 1
        except IOError:
            raise
        except Exception:
            raise

    def compute_sum(self):
        """
        This function creates the weighted sum for each date of the CDI
            If any input data array is completely empty for a given data, the sum is set to empty data for that date
        Returns:
            None: data is written directly to the output NetCDF file
        """
        output_file = os.path.join(self.__output_dir, "STEP_0301_CDI_weighted_sum_{}.nc".format(self.__region))
        output_data_set = None
        try:
            # create the output file #
            print("Initializing the weighted sum file.")
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__common_times,
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)
            # variables #
            cdi_sum = output_data_set.createVariable('cdi_weighted_sum', 'float32', ('time', 'latitude', 'longitude'))
            cdi_sum.units = '1'
            cdi_sum.missing_value = self.__missing
            cdi_sum.standard_name = "cdi_weighted_sum"
            cdi_sum.long_name = "Weighted Composite Drought Indicator"

            # determine the data ranges for each parameter #
            data_ranges = {}
            for param in self.__cdi_inputs:
                data_ranges[param] = self.__get_time_range(param)

            # load the data from each source using the common dates #
            print("Processing CDI values...")
            for t in range(0, len(self.__common_times)):
                cdi_weight_sum = None
                valid_data = True
                for param in self.__cdi_inputs:
                    # get the applicable data #
                    data = ma.masked_equal(netcdf.extract_data(self.__datasets[param], self.__parameter_names[param],
                                                               data_ranges[param][t]), self.__missing)
                    # verify we have data to add to the sum #
                    if np.amax(data) < 0.0:
                        valid_data = False
                    else:
                        # weight the data #
                        weighted_data = data * self.__cdi_weights[param]
                        # update the weighted sum #
                        if cdi_weight_sum is None:
                            cdi_weight_sum = weighted_data
                        else:
                            cdi_weight_sum += weighted_data
                # add the weighted sum to the NetCDF file #
                if valid_data:
                    cdi_sum[t] = cdi_weight_sum.filled(self.__missing)
                else:
                    cdi_sum[t] = self.__empty_set
        except ValueError:
            raise
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()


def main():
    """
    This is the main entry point for the program
    """
    script_start = datetime.now()
    try:
        # initialize a new soil moisture class #
        cdi = CompositeDroughtIndicator()
        # get the common dates between the sets #
        cdi.get_common_dates()
        # compute the weighted sum #
        cdi.compute_sum()
    except ValueError as ve:
        print(ve)
    except IOError as ioe:
        print(ioe)
    except Exception as ex:
        print(ex)
    finally:
        script_end = datetime.now()
        print("Script execution: {}".format(script_end - script_start))


if __name__ == '__main__':
    main()
