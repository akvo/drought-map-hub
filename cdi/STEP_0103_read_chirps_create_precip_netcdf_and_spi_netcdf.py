# -*- coding: utf-8 -*-
import os
from libs.config_reader import ConfigParser
from libs.file_operations import FileHandler
from libs.subgrid_calculations import CHIRPSSubGrid
from libs.statistics_operations import StatisticOperations
import libs.netcdf_functions as netcdf
from libs.spi_calculations import calculate_monthly_spi as spi_calc
from argparse import ArgumentParser
import numpy as np
import numpy.ma as ma
import re
from datetime import datetime, date, timedelta


class StandardizedPrecipitationIndex:
    """
    This is the core processing class for executing all SPI (standardized precipitation index) operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__spi_periods = sorted(self.__config.get('spi_periods'))
        self.__raw_data_dir = self.__config.get('raw_data_dirs', 'chirps_tif').replace("\\", '/')
        self.__working_dir = self.__config.get('scratch_dir').replace("\\", '/') + '/SPI'
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__file_patterns = self.__config.get('file_patterns')
        self.__file_patterns['chirps_netcdf_regex'] = "STEP_0103_CHIRPS_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__file_patterns['spi_netcdf_regex'] = "STEP_0103_SPI_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__fileHandler = FileHandler(
            raw_data_dir=self.__raw_data_dir,
            working_dir=self.__working_dir,
            file_patterns=self.__file_patterns
        )
        self.__raw_file_match = re.compile(r'{}'.format(self.__file_patterns['chirps_tif_regex']))
        self.__working_chirps_file_match = re.compile(r'{}'.format(self.__file_patterns['chirps_netcdf_regex']))
        self.__working_spi_file_match = re.compile(r'{}'.format(self.__file_patterns['spi_netcdf_regex']))
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__missing = -9999.0
        self.netcdf_files = []
        self.__precip_times = []
        self.__start_index = {}

    def __get_chirps_date(self, file_name):
        """
        This function parses the CHIRPS file name to determine the year/month string for the valid time
        Args:
            file_name (str): name of the CHIRPS file

        Returns:
            String of the year/month values in 'YYYYMM' format
        """
        (year, month) = self.__raw_file_match.match(file_name).groups()
        return "{}{}".format(year, month)

    def __get_chirps_calendar_value(self, file_name):
        """
        This function parses the CHIRPS file name to calculate the number of days since Jan 1, 1900 for the valid time
        Args:
            file_name (str): name of the CHIRPS file

        Returns:
            Integer value of the number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        (year, month) = self.__raw_file_match.match(file_name).groups()
        test_date = date(int(year), int(month), 1)
        time_delta = test_date - origin_date
        return int(time_delta.days)

    def __get_spi_calendar_value(self, file_name):
        """
        This function parses the SPI file name to calculate the number of days since Jan 1, 1900 for the valid time
        Args:
            file_name (str): name of the SPI file

        Returns:
            Integer value of the number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        (year, month) = self.__working_spi_file_match.match(file_name).groups()
        test_date = date(int(year), int(month), 1)
        time_delta = test_date - origin_date
        return int(time_delta.days)

    @staticmethod
    def __get_calendar_times(files, match_regex):
        """
        This function builds a list of the valid times as days since Jan 1, 1900
        Args:
            files: list of the file names as strings
            match_regex: regex of the file name pattern to parse

        Returns:
            List (floats) of the valid times as number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        times = []
        for f in files:
            (year, month) = match_regex.match(f).groups()
            test_date = date(int(year), int(month), 1)
            time_delta = test_date - origin_date
            times.append(float(time_delta.days))
        return times

    def __get_calendar_times_by_month(self, desired_month, period):
        """
        This function determines the time index values from the list of available dates that match a particular month of the year
        Args:
            desired_month (int): numeric value of the month (1 - 12)

        Returns:
            list of the indices that match the desired dates
        """
        try:
            origin_date = date(1900, 1, 1)
            indices = []
            # loop thru the times of the precip file and find the indices by month #
            for i in range(self.__start_index[period], len(self.__precip_times)):
                time = self.__precip_times[i]
                valid_time = origin_date + timedelta(days=int(time))
                if valid_time.month == desired_month:
                    indices.append(i)
            return indices
        except ValueError:
            raise
        except Exception:
            raise

    def __get_chirps_files_by_month(self, month):
        """
        This function reads the working data directory to find available files to process by month
        Returns:
            List of fully-qualified names
        """
        results = []
        try:
            test_pattern = self.__file_patterns['chirps_netcdf_regex'].split('(0')[0] + str(month) + "\\.nc"
            file_test = re.compile(r'{}'.format(test_pattern))

            results = [
                f for f in sorted(os.listdir(self.__working_dir))
                if file_test.match(f)
            ]
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            return results

    def __get_precip_from_netcdf(self, file_name):
        """
        This function extracts the precipitation values from a CHIRPS NetCDF file
        Args:
            file_name (str): name of the CHIRPS NetCDF to read

        Returns:
            numpy 2D array of precipitation values for the month
        """
        dataset = None
        values = []
        try:
            file_path = '{}/{}'.format(self.__working_dir, file_name)
            dataset = netcdf.open_dataset(file_path)
            values = netcdf.extract_data(dataset, 'precip_mm')
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if dataset is not None:
                dataset.close()
            return values

    def __create_spi_data_from_precip(self, month, period):
        """
        This function loads the precipitation values for a particular month and desired totaling period (1-month, 3-month, etc.)
            and calculates the SPI for that data
        Args:
            month (int): the numeric value of the month (1 - 12)
            period (int): the numeric value of the totaling period

        Returns:
            list of 2D numpy arrays, and a list of the time dimension indices
        """
        precip_file = os.path.join(self.__working_dir, "STEP_0103_Precip_Totals_{}.nc".format(self.__region))
        input_dataset = netcdf.open_dataset(precip_file)
        try:
            precip_values = []
            # determine the time positions for the month #
            times = self.__get_calendar_times_by_month(month, period)
            # extract the period precipitation values for the month series #
            for t in times:
                v = netcdf.extract_data(input_dataset, 'precip_{}_month'.format(period), t)
                precip_values.append(np.where(v == self.__missing, 0.0, v))
            # compute the SPI values #
            spi_values = spi_calc(precip_values)
            # cleanup memory #
            del precip_values
            # return the SPI values #
            return spi_values, times
        except ValueError:
            raise
        except IOError:
            raise
        except Exception:
            raise
        finally:
            input_dataset.close()

    def get_chirps_files_to_process(self, all_tif=False):
        """
        This function gets the list of TIF files to convert to NetCDF subsets
        Args:
            all_tif (boolean): optional flag to process all TIF files, even if NetCDF versions exist

        Returns:
            List of strings of the TIF file names
        """
        files = []
        try:
            raw_files = self.__fileHandler.get_raw_file_names('chirps_tif_regex')
            if all_tif:  # include all TIF files
                files = raw_files
            else:  # determine which TIF files have not been converted to NetCDF
                working_files = self.__fileHandler.get_working_file_names('chirps_netcdf_regex')
                # compare the raw files with the processed files #
                for f in raw_files:
                    # parse out the year/days from the file name #
                    (year, month) = self.__raw_file_match.match(f).groups()
                    file_date = "{}{}".format(year, month)
                    # prepare the NetCDF filename to test for #
                    test_file = "STEP_0103_CHIRPS_{}_{}.nc".format(self.__region, file_date)
                    if test_file not in working_files:
                        # add the file name to the list to process #
                        files.append(f)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return files

    def create_chirps_netcdf_file(self, file_name):
        """
        This function reads the values from a CHIRPS TIF file and creates a NetCDF file of the subset data for the current region
        Args:
            file_name (str): the name of the TIF file to process

        Returns:
            None: results are a NetCDF file created in the working directory for the particular year/month
        """
        raw_file_path = "{}/{}".format(self.__raw_data_dir, file_name)
        file_date = self.__get_chirps_date(file_name)
        output_file = os.path.join(self.__working_dir, "STEP_0103_CHIRPS_{}_{}.nc".format(self.__region, file_date))
        output_data_set = None
        try:
            # extract SubGrids of the required parameters #
            with CHIRPSSubGrid(self.__bounds, raw_file_path) as sg:
                precip_data = sg.create_sub_grid()

            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': [self.__get_chirps_calendar_value(file_name)],
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)

            # add precipitation data to output data set #
            precip_var = output_data_set.createVariable('precip_mm', 'float32', ('time', 'latitude', 'longitude'))
            precip_var.units = "mm"
            precip_var.missing_value = self.__missing
            precip_var.long_name = "Monthly precipitation amount"
            precip_var[0] = precip_data
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def create_precip_from_chirps(self):
        """
        This function takes the precipitation data from the individual dates and adds monthly-period totals to a single NetCDF file.
            The list of periods to process are set int the configuration file.
            Example: the configuration lists periods of 1 and 3
                for the 1-month periods the values are simply copied to the new file
                for the 3-month periods, the first 2 available months do not have any data; the 3rd available month uses the sum of values from months 1-3
                    each following month is the sum of that month and the previous two months
        Returns:
            None: data is directly written to the output NetCDF file
        """
        output_file = os.path.join(self.__working_dir, "STEP_0103_Precip_Totals_{}.nc".format(self.__region))
        output_data_set = None
        min_range = min(self.__spi_periods)
        max_range = max(self.__spi_periods)
        try:
            chirps_files = sorted(self.__fileHandler.get_working_file_names('chirps_netcdf_regex'))

            # get the valid times of the totals #
            self.__precip_times = self.__get_calendar_times(chirps_files, self.__working_chirps_file_match)

            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__precip_times,
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)

            # add precipitation data to output data set #
            rows = len(self.__latitudes)
            columns = len(self.__longitudes)
            precip_vars = []
            empty_set = np.full((rows, columns), self.__missing)
            for p in self.__spi_periods:
                self.__start_index[p] = (p - 1)
                precip_var = output_data_set.createVariable('precip_{}_month'.format(p), 'float32', ('time', 'latitude', 'longitude'))
                precip_var.units = "mm"
                precip_var.missing_value = self.__missing
                precip_var.long_name = "{} Month precipitation amount".format(p)
                for t in range(0, len(self.__precip_times)):
                    precip_var[t] = empty_set
                precip_vars.append(precip_var)
            # separate 1-month periods from any that need totals #
            if min_range == 1:
                for i in range(0, len(chirps_files)):
                    precip_vars[0][i] = self.__get_precip_from_netcdf(chirps_files[i])
            # continue with the remaining periods #
            if max_range > 1:
                # load the range of the longest period, minus 1 month #
                precip_values = []
                for i in range(0, max_range):
                    precip_values.append(self.__get_precip_from_netcdf(chirps_files[i]))
                # loop thru the remaining times and create the monthly totals #
                for i in range((max_range - 1), len(chirps_files)):
                    offset = i - (max_range - 1)
                    # load the current month #
                    precip_values.append(self.__get_precip_from_netcdf(chirps_files[i]))
                    # compute the monthly totals and append the values to the output array #
                    for j, period in enumerate(self.__spi_periods):
                        # determine the number of sub-totals within the max range period #
                        """
                        Example: assuming we want SPI values for 3-month, and 9-month ranges
                            Our maximum range is 9 months for the current data set
                            We have:
                                7 3-month values starting at the 3rd index
                                1 9-month value starting at the 9th index
                        """
                        if period > 1:
                            first = 0
                            last = period
                            # loop thru the current subset of precipitation values and create the totals #
                            for s in range(self.__start_index[period], max_range):
                                first += 1
                                last += 1
                                total_precip = ma.sum(ma.masked_equal(precip_values[first:last], self.__missing), axis=0)
                                precip_vars[j][s + offset] = total_precip.filled(self.__missing)
                    # remove the first date from the precip array #
                    precip_values = precip_values[1:]
                del precip_values
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def create_spi_anomaly_file(self):
        """
        This function processes the SPI per month series and adds the anomaly values to the final NetCDF file
        """
        output_file = os.path.join(self.__output_dir, "STEP_0103_SPI_anomaly_{}.nc".format(self.__region))
        try:
            # initialize the SPI anomaly file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__precip_times,
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            print("Creating SPI anomaly file")
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)
            # add SPI anomaly to output data set #
            rows = len(self.__latitudes)
            columns = len(self.__longitudes)
            empty_set = np.full((rows, columns), self.__missing)
            for p in self.__spi_periods:
                spi_var = output_data_set.createVariable('spi_{}_anom'.format(p), 'float32', ('time', 'latitude', 'longitude'))
                spi_var.units = "none"
                spi_var.missing_value = self.__missing
                spi_var.long_name = "Monthly SPI anomaly ({} month precip totals)".format(p)
                for t in range(0, self.__start_index[p]):
                    spi_var[t] = empty_set
            # close the file and cleanup memory $
            output_data_set.close()
            del rows, columns, empty_set

            # loop thru the months and compute the anomaly series #
            stats_ops = StatisticOperations()
            for i, p in enumerate(self.__spi_periods):
                # open the NetCDF file in append mode #
                output_data_set = netcdf.open_dataset(output_file, 'a')
                spi_var = output_data_set.variables['spi_{}_anom'.format(p)]
                for m in range(1, 13):
                    # compute the spi values #
                    (spi, times) = self.__create_spi_data_from_precip(m, p)
                    # compute the monthly anomalies #
                    anomalies = stats_ops.compute_anomalies_from_values(spi)
                    # cleanup memory #
                    del spi
                    # add the anomalies to the NetCDF file #
                    for idx, t in enumerate(times):
                        spi_var[t] = anomalies[idx]
                    # cleanup memory #
                    del anomalies
                # close file to write the data #
                output_data_set.close()
                print("-- SPI anomalies calculated for {}-month totals".format(p))
        except IOError:
            raise
        except ValueError:
            raise
        except Exception:
            raise


def main(args):
    """
    This is the main entry point for the program
    """
    script_start = datetime.now()
    mode = str(args.mode)
    try:
        # initialize a new SPI class #
        spi = StandardizedPrecipitationIndex()

        # determine the files to process #
        if mode == 'all':
            print("Processing all files for CHIRPS.")
            files_to_process = spi.get_chirps_files_to_process(True)
        else:
            files_to_process = spi.get_chirps_files_to_process()
            if len(files_to_process) == 0:
                print("All files have been processed for CHIRPS.")
            else:
                print("Processing needed files for CHIRPS.")
        # convert any unprocessed TIF files to NetCDF format #
        for f in files_to_process:
            spi.create_chirps_netcdf_file(f)

        # create the 3-month precip totals #
        print("Creating precipitation totals")
        spi.create_precip_from_chirps()

        # create the SPI anomaly file #
        spi.create_spi_anomaly_file()
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
    # set up the command line argument parser
    parser = ArgumentParser()
    parser.add_argument("-m", "--mode", default="updates",
                        help="The mode of the current processing: updates or all. Default is updates")
    # execute the programs with the supplied options
    main(parser.parse_args())
