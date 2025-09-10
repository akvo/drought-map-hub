# -*- coding: utf-8 -*-
import os
import subprocess
from libs.config_reader import ConfigParser
from libs.file_operations import FileHandler
from libs.subgrid_calculations import HDFSubGrid
from libs.statistics_operations import StatisticOperations
import libs.netcdf_functions as netcdf
from argparse import ArgumentParser
import numpy as np
import numpy.ma as ma
import re
from datetime import datetime, date, timedelta


class NormalizedDifferenceVegetationIndex:
    """
    This is the core processing class for executing all NDVI (normalized difference vegetation index) operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__raw_data_dir = self.__config.get('raw_data_dirs', 'ndvi_hdf').replace("\\", '/')
        self.__working_dir = self.__config.get('scratch_dir').replace("\\", '/') + '/NDVI'
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__hdf_group = self.__config.get('hdf_groups', 'ndvi')
        self.__file_patterns = self.__config.get('file_patterns')
        self.__file_patterns['ndvi_netcdf_regex'] = "STEP_0102_NDVI_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__fileHandler = FileHandler(
            raw_data_dir=self.__raw_data_dir,
            working_dir=self.__working_dir,
            file_patterns=self.__file_patterns
        )
        self.__raw_file_match = re.compile(r'{}'.format(self.__file_patterns['ndvi_hdf_regex']))
        self.__working_file_match = re.compile(r'{}'.format(self.__file_patterns['ndvi_netcdf_regex']))
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__missing = -9999.0
        self.netcdf_files = []

    def __get_hdf_date(self, file_name):
        """
        This function parses the HDF file name to determine the year/month string for the valid time
        Args:
            file_name (str): name of the HDF file

        Returns:
            String of the year/month values in 'YYYYMM' format
        """
        (year, days) = self.__raw_file_match.match(file_name).groups()
        test_date = date(int(year), 1, 1) + timedelta(days=int(days))
        return test_date.strftime("%Y%m")

    def __get_calendar_value(self, file_name):
        """
        This function parses the HDF file name to calculate the number of days since Jan 1, 1900 for the valid time
        Args:
            file_name (str): name of the HDF file

        Returns:
            Integer value of the number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        (year, days) = self.__raw_file_match.match(file_name).groups()
        test_date = date(int(year), 1, 1) + timedelta(days=(int(days) - 1))
        time_delta = test_date - origin_date
        return int(time_delta.days)

    def __get_calendar_times(self, files):
        """
        This function builds a list of the valid times as days since Jan 1, 1900
        Args:
            files: list of the HDF file names as strings

        Returns:
            List (floats) of the valid times as number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        times = []
        for f in files:
            (year, month) = self.__working_file_match.match(f).groups()
            test_date = date(int(year), int(month), 1)
            time_delta = test_date - origin_date
            times.append(float(time_delta.days))
        return times

    def __get_ndvi_files_by_month(self, month):
        """
        This function reads the working data directory to find available files to process by month
        Returns:
            List of fully-qualified names
        """
        results = []
        try:
            test_pattern = self.__file_patterns['ndvi_netcdf_regex'].split('(0')[0] + str(month) + "\\.nc"
            file_test = re.compile(r'{}'.format(test_pattern))

            results = [
                '{}/{}'.format(self.__working_dir, f) for f in sorted(os.listdir(self.__working_dir))
                if file_test.match(f)
            ]
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            return results

    def convert_h4_to_h5(self):
        """

        Returns:

        """
        try:
            raw_files = self.__fileHandler.get_raw_file_names('ndvi_hdf_regex')
            for f in raw_files:
                if f.find("_h5") < 0:
                    raw_file_path = "{}/{}".format(self.__raw_data_dir, f)
                    file_name = raw_file_path.split('.hdf')[0]
                    h5_path = file_name + '_h5.hdf'
                    subprocess.run('./libs/h4toh5convert {} {}'.format(raw_file_path, h5_path), shell=True, check=True)
                    os.remove(raw_file_path)

        except IOError:
            raise
        except Exception:
            raise

    def get_files_to_process(self, all_hdf=False):
        """
        This function gets the list of HDF files to convert to NetCDF subsets
        Args:
            all_hdf (boolean): optional flag to process all HDF files, even if NetCDF versions exist

        Returns:
            List of strings of the HDF file names
        """
        files = []
        try:
            raw_files = self.__fileHandler.get_raw_file_names('ndvi_hdf_regex')
            if all_hdf:  # include all HDF files
                files = raw_files
            else:  # determine which HDF files have not been converted to NetCDF
                working_files = self.__fileHandler.get_working_file_names('ndvi_netcdf_regex')
                # parse out the year/days from the file name #
                for f in raw_files:
                    file_date = self.__get_hdf_date(f)
                    test_file = "STEP_0102_NDVI_{}_{}.nc".format(self.__region, file_date)
                    if test_file not in working_files:
                        files.append(f)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return files

    def create_ndvi_netcdf_file(self, file_name):
        """
        This function reads the required parameters from a HDF file and creates a NetCDF file of the subset data for the current region
        Args:
            file_name (str): the name of the HDF file to process

        Returns:
            None: results are a NetCDF file created in the working directory for the particular year/month
        """
        raw_file_path = "{}/{}".format(self.__raw_data_dir, file_name)
        file_date = self.__get_hdf_date(file_name)
        output_file = os.path.join(self.__working_dir, "STEP_0102_NDVI_{}_{}.nc".format(self.__region, file_date))
        output_data_set = None
        try:
            # extract SubGrids of the required parameters #
            with HDFSubGrid(self.__bounds, raw_file_path, self.__hdf_group) as sg:
                ndvi_data = sg.create_sub_grid('CMG 0.05 Deg Monthly NDVI') * 0.0001  # data is scaled in the HDF file
                qc_data = sg.create_sub_grid('CMG 0.05 Deg Monthly VI Quality')

            # filter the NDVI data by quality #
            qc_filter = np.logical_or(np.logical_or(np.logical_and(qc_data > 17407, qc_data < 18432), qc_data < 11263), ndvi_data == -0.3)
            data_mask = ma.masked_where(qc_filter, ndvi_data)
            filtered_ndvi_data = data_mask.filled(self.__missing)

            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': [self.__get_calendar_value(file_name)],
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)

            # add NDVI data to output data set #
            ndvi_var = output_data_set.createVariable('NDVI', 'float32', ('time', 'latitude', 'longitude'))
            ndvi_var.units = "NDVI"
            ndvi_var.missing_value = self.__missing
            ndvi_var.long_name = "Monthly QC filtered NDVI data"
            ndvi_var[0] = filtered_ndvi_data
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def update_ndvi_anomaly_file(self):
        """
        This function processes the files for a particular month and adds the anomaly arrays to the final NetCDF file
        """
        output_file = os.path.join(self.__output_dir, "STEP_0102_NDVI_anomaly_{}.nc".format(self.__region))
        output_data_set = None
        try:
            # get list of NDVI NetCDF files #
            self.netcdf_files = sorted(self.__fileHandler.get_working_file_names('ndvi_netcdf_regex'))
            # initialize the NDVI anomaly file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__get_calendar_times(self.netcdf_files),
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            print("Creating NDVI anomaly file")
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)
            # add NDVI anomalies to output data set #
            ndvi_var = output_data_set.createVariable('ndvi_anom', 'float32', ('time', 'latitude', 'longitude'))
            ndvi_var.units = "NDVI"
            ndvi_var.missing_value = self.__missing
            ndvi_var.long_name = "Monthly NDVI anomaly"

            # determine the order of the months #
            month_list = []
            for m in range(0, 12):
                null, month = self.__working_file_match.match(self.netcdf_files[m]).groups()
                month_list.append(month)
            # loop thru months and process the anomaly per year #
            stats_ops = StatisticOperations()
            for idx, m in enumerate(month_list):
                # get the list of files for a particular month #
                files = self.__get_ndvi_files_by_month(m)
                # compute the NDVI anomalies per year for a particular month #
                month_anomalies = stats_ops.compute_anomalies_from_files(files, "NDVI")
                # set the starting index to the month index #
                index = idx
                # loop thru the years and add the data to the NetCDF file #
                for y in month_anomalies:
                    ndvi_var[index] = y
                    index += 12  # increment 1 year
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()


def main(args):
    """
    This is the main entry point for the program
    """
    script_start = datetime.now()
    mode = str(args.mode)
    try:
        # initialize a new NDVI class #
        ndvi = NormalizedDifferenceVegetationIndex()

        # verify raw files are HDF5 format #
        ndvi.convert_h4_to_h5()

        # determine the files to process #
        if mode == 'all':
            print("Processing all months for NDVI.")
            files_to_process = ndvi.get_files_to_process(True)
        else:
            files_to_process = ndvi.get_files_to_process()
            if len(files_to_process) == 0:
                print("All months have been processed for NDVI.")
            else:
                print("Processing needed months for NDVI.")

        # convert any unprocessed HDF files to NetCDF format #
        for f in files_to_process:
            ndvi.create_ndvi_netcdf_file(f)

        # create the NDVI anomaly file #
        ndvi.update_ndvi_anomaly_file()
    except IOError as ioe:
        print(ioe)
    except Exception as ex:
        print(ex)
    finally:
        script_end = datetime.now()
        print("Script execution: {}".format(script_end - script_start))


if __name__ == '__main__':
    # set up the command line argument parser
    parser = ArgumentParser()
    parser.add_argument("-m", "--mode", default="updates",
                        help="The mode of the current processing: updates or all. Default is updates")
    # execute the programs with the supplied options
    main(parser.parse_args())
