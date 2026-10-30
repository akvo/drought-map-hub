# -*- coding: utf-8 -*-
import os
import sys
from libs.config_reader import ConfigParser
import libs.netcdf_functions as netcdf
import numpy as np
import numpy.ma as ma


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
            "esi": os.path.join(self.__output_dir, "STEP_0100_ESI_pct_rank_{}.nc".format(self.__region)),
            "evi2": os.path.join(self.__output_dir, "STEP_0100_EVI2_pct_rank_{}.nc".format(self.__region)),
            "spi": os.path.join(self.__output_dir, "STEP_0100_SPI_pct_rank_{}.nc".format(self.__region)),
            "sm": os.path.join(self.__output_dir, "STEP_0100_SM_pct_rank_{}.nc".format(self.__region))
        }
        self.__cdi_inputs = []
        self.__datasets = {}
        self.__common_times = []
        self.__times = {}
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
        # Use a tolerance: floating-point sums such as 0.3+0.3+0.3+0.1 do not
        # land exactly on 1.0, so an equality check would reject valid configs.
        if abs(total_weight - 1.0) > 1e-6:
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

    def close(self):
        """
        Release the input NetCDF handles.

        The process used to exit immediately after this step, so leaking them
        was invisible. HDF5 keeps a lock on an open file, so a second run in
        the same process cannot recreate the STEP_0100 outputs until these are
        closed - which is exactly what the integration tests do.
        """
        for data_set in self.__datasets.values():
            data_set.close()
        self.__datasets = {}

    def __get_time_indices(self, source):
        """
        Map every common date to its index in this source's own time axis.

        The common dates are NOT contiguous. NDMC publishes no EVI2 for January,
        July or August, so those months drop out of the intersection while
        ESI/SPI/SM still carry them. The previous implementation returned a
        contiguous range(start, end) and indexed it positionally, which walked
        the gap-free inputs past the gaps and blended progressively earlier
        months into each raster - by the end of the series it was reading
        2025-09 ESI/SPI/SM into the CDI labelled 2026-05.

        Looking each date up by value keeps every input on the same month.

        Args:
            source (str): the name of the input parameter

        Returns:
            list of indices, aligned element-wise with self.__common_times
        """
        try:
            lookup = {t: i for i, t in enumerate(self.__times[source])}
            return [lookup[t] for t in self.__common_times]
        except KeyError:
            raise
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

            # resolve each common date to a per-parameter time index #
            data_ranges = {}
            for param in self.__cdi_inputs:
                data_ranges[param] = self.__get_time_indices(param)

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
    # initialize a new soil moisture class #
    cdi = CompositeDroughtIndicator()
    try:
        # get the common dates between the sets #
        cdi.get_common_dates()
        # compute the weighted sum #
        cdi.compute_sum()
    finally:
        cdi.close()


if __name__ == '__main__':
    main()
