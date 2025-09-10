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


class LandSurfaceTemp:
    """
    This is the core processing class for executing all Land-Surface Temperature operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__raw_data_dir = self.__config.get('raw_data_dirs', 'lst_hdf').replace("\\", '/')
        self.__working_dir = self.__config.get('scratch_dir').replace("\\", '/') + '/LST'
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__hdf_group = self.__config.get('hdf_groups', 'lst')
        self.__file_patterns = self.__config.get('file_patterns')
        self.__file_patterns['lst_netcdf_regex'] = "STEP_0101_LST_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__fileHandler = FileHandler(
            raw_data_dir=self.__raw_data_dir,
            working_dir=self.__working_dir,
            file_patterns=self.__file_patterns
        )
        self.__raw_file_match = re.compile(r'{}'.format(self.__file_patterns['lst_hdf_regex']))
        self.__working_file_match = re.compile(r'{}'.format(self.__file_patterns['lst_netcdf_regex']))
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
        if file_name.find('/') > -1:
            file_name = file_name.split('/')[1]
        match = self.__raw_file_match.match(file_name)
        (year, day_of_year) = match.groups()
        test_date = datetime.strptime(year + "-" + day_of_year, "%Y-%j")
        return test_date.strftime("%Y%m")

    def __get_calendar_value(self, file_name):
        """
        This function parses the HDF file name to calculate the number of days since Jan 1, 1900 for the valid time
        Args:
            file_name (str): name of the HDF file

        Returns:
            Integer value of the number of days since Jan 1, 1900
        """
        if file_name.find('/') > -1:
            file_name = file_name.split('/')[1]
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

    def __get_lst_files_by_month(self, month):
        """
        This function reads the working data directory to find available files to process by month
        Returns:
            List of fully-qualified names
        """
        results = []
        try:
            test_pattern = self.__file_patterns['lst_netcdf_regex'].split('(0')[0] + str(month) + "\\.nc"
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
            raw_files = self.__fileHandler.get_raw_file_names('lst_hdf_regex')
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
            raw_files = sorted(self.__fileHandler.get_raw_file_names('lst_hdf_regex'), reverse=True)
            if all_hdf:  # include all HDF files
                files = raw_files
            else:  # determine which HDF files have not been converted to NetCDF
                working_files = self.__fileHandler.get_working_file_names('lst_netcdf_regex')
                # parse out the year/days from the file name #
                for f in raw_files:
                    name = f
                    if name.find('/') > -1:
                        name = name.split('/')[1]
                    file_date = self.__get_hdf_date(name)
                    test_file = "STEP_0101_LST_{}_{}.nc".format(self.__region, file_date)
                    if test_file not in working_files:
                        files.append(f)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return files

    def create_lst_netcdf_file(self, file_name):
        """
        This function reads the required parameters from a HDF file and creates a NetCDF file of the subset data for the current region
        Args:
            file_name (str): the name of the HDF file to process

        Returns:
            None: results are a NetCDF file created in the working directory for the particular year/month
        """
        raw_file_path = "{}/{}".format(self.__raw_data_dir, file_name)
        file_date = self.__get_hdf_date(file_name)
        output_file = os.path.join(self.__working_dir, "STEP_0101_LST_{}_{}.nc".format(self.__region, file_date))
        output_data_set = None
        try:

            # extract SubGrids of the required parameters #
            with HDFSubGrid(self.__bounds, raw_file_path, self.__hdf_group) as sg:
                lst_day = sg.create_sub_grid('LST_Day').astype(float) * 0.02  # data is scaled in the HDF file
                lst_night = sg.create_sub_grid('LST_Night').astype(float) * 0.02  # data is scaled in the HDF file
                qc_day = sg.create_sub_grid('QC_Day')
                qc_night = sg.create_sub_grid('QC_Night')

            # compute the LST delta #
            filtered_lst_day = ma.masked_where(np.logical_or(qc_day < 16, lst_day == 0), lst_day)
            filtered_lst_night = ma.masked_where(np.logical_or(qc_night < 16, lst_night == 0), lst_night)
            delta = np.ma.clip(np.ma.subtract(filtered_lst_day, filtered_lst_night), -40.0, 40.0)
            lst_delta = np.round(delta.filled(self.__missing), 3)

            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': [self.__get_calendar_value(file_name)],
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)

            # add LST delta to output data set #
            lst_var = output_data_set.createVariable('LST_Delta', 'float32', ('time', 'latitude', 'longitude'))
            lst_var.units = "K"
            lst_var.missing_value = self.__missing
            lst_var.long_name = "Monthly Land-surface Temperature Day-Night delta"
            lst_var[0] = lst_delta
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def update_lst_anomaly_file(self):
        """
        This function processes the files for a particular month and adds the anomaly arrays to the final NetCDF file
        """
        output_file = os.path.join(self.__output_dir, "STEP_0101_LST_anomaly_{}.nc".format(self.__region))
        output_data_set = None
        try:
            # get list of LST NetCDF files #
            self.netcdf_files = sorted(self.__fileHandler.get_working_file_names('lst_netcdf_regex'))
            # initialize the LST anomaly file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__get_calendar_times(self.netcdf_files),
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            print("Creating LST anomaly file")
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)
            # add LST delta to output data set #
            lst_var = output_data_set.createVariable('lst_anom', 'float32', ('time', 'latitude', 'longitude'))
            lst_var.units = "K"
            lst_var.missing_value = self.__missing
            lst_var.long_name = "Monthly Land-surface Temperature anomaly"

            # determine the order of the months #
            month_list = []
            for m in range(0, 12):
                null, month = self.__working_file_match.match(self.netcdf_files[m]).groups()
                month_list.append(month)
            # loop thru months and process the anomaly per year #
            stats_ops = StatisticOperations()
            for idx, m in enumerate(month_list):
                # get the list of files for a particular month #
                files = self.__get_lst_files_by_month(m)
                # compute the LST anomalies per year for a particular month #
                month_anomalies = stats_ops.compute_anomalies_from_files(files, "LST_Delta")
                # set the starting index to the month index #
                index = idx
                # loop thru the years and add the data to the NetCDF file #
                for y in month_anomalies:
                    lst_var[index] = y
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
        # initialize a new LST class #
        lst = LandSurfaceTemp()

        lst.convert_h4_to_h5()

        # determine the files to process #
        if mode == 'all':
            print("Processing all months for LST.")
            files_to_process = lst.get_files_to_process(True)
        else:
            files_to_process = lst.get_files_to_process()
            if len(files_to_process) == 0:
                print("All months have been processed for LST.")
            else:
                print("Processing needed months for LST.")

        # convert any unprocessed HDF files to NetCDF format #
        for f in files_to_process:
            lst.create_lst_netcdf_file(f)

        # create the LST anomaly file #
        lst.update_lst_anomaly_file()
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
