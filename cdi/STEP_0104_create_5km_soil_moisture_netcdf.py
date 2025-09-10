# -*- coding: utf-8 -*-
import os
from libs.config_reader import ConfigParser
from libs.file_operations import FileHandler
from libs.subgrid_calculations import NetCDFSubGrid
import libs.netcdf_functions as netcdf
from argparse import ArgumentParser
import numpy as np
import re
from datetime import datetime, date


class SoilMoisture:
    """
    This is the core processing class for executing all soil moisture creation operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__raw_data_dir = self.__config.get('raw_data_dirs', 'fldas_data').replace("\\", '/')
        self.__working_dir = self.__config.get('scratch_dir').replace("\\", '/') + '/SM'
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__file_patterns = self.__config.get('file_patterns')
        self.__file_patterns['sm_netcdf_regex'] = "STEP_0104_SM_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__fileHandler = FileHandler(
            raw_data_dir=self.__raw_data_dir,
            working_dir=self.__working_dir,
            file_patterns=self.__file_patterns
        )
        self.__raw_file_match = re.compile(r'{}'.format(self.__file_patterns['fldas_data_regex']))
        self.__working_file_match = re.compile(r'{}'.format(self.__file_patterns['sm_netcdf_regex']))
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__missing = -9999.0
        self.__soil_units = ""

    def __get_fldas_date(self, file_name):
        """
        This function parses the FLDAS file name to determine the year/month string for the valid time
        Args:
            file_name (str): name of the FLDAS file

        Returns:
            String of the year/month values in 'YYYYMM' format
        """
        (year, month) = self.__raw_file_match.match(file_name).groups()
        return "{}{}".format(year, month)

    def __get_fldas_calendar_value(self, file_name):
        """
        This function parses the FLDAS file name to calculate the number of days since Jan 1, 1900 for the valid time
        Args:
            file_name (str): name of the FLDAS file

        Returns:
            Integer value of the number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        (year, month) = self.__raw_file_match.match(file_name).groups()
        test_date = date(int(year), int(month), 1)
        time_delta = test_date - origin_date
        return int(time_delta.days)

    def get_fldas_files_to_process(self, all_dates=False):
        """
        This function gets the list of FLDAS files to convert to Soil Moisture subsets
        Args:
            all_dates (boolean): optional flag to process all dates files, even if Soil Moisture versions exist

        Returns:
            List of strings of the FLDAS file names
        """
        files = []
        try:
            raw_files = self.__fileHandler.get_raw_file_names('fldas_data_regex')
            if all_dates:  # include all FLDAS files
                files = raw_files
            else:  # determine which FLDAS files have not been converted to Soil Moisture SubGrids
                working_files = self.__fileHandler.get_working_file_names('sm_netcdf_regex')
                # compare the raw files with the processed files #
                for f in raw_files:
                    # parse out the year/days from the file name #
                    (year, month) = self.__raw_file_match.match(f).groups()
                    file_date = "{}{}".format(year, month)
                    # prepare the NetCDF filename to test for #
                    test_file = "STEP_0104_SM_{}_{}.nc".format(self.__region, file_date)
                    if test_file not in working_files:
                        # add the file name to the list to process #
                        files.append(f)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return files

    def __create_soil_moisture_parameters(self, file_path):
        """
        This functions calculates the weighted values for the 2 "root zones" and the total soil moisture column using the 4 data sets in the global FLDAS files
        Args:
            file_path (str): fully qualified path of the FLDAS file

        Returns:
            Three 2D numpy arrays of floats
        """
        # initialize parameters #
        try:
            # create the SubGrids of the raw data #
            with NetCDFSubGrid(self.__bounds, file_path, True) as sg:
                soil_00_10 = sg.create_sub_grid('SoilMoi00_10cm_tavg')
                soil_10_40 = sg.create_sub_grid('SoilMoi10_40cm_tavg')
                soil_40_100 = sg.create_sub_grid('SoilMoi40_100cm_tavg')
                soil_100_200 = sg.create_sub_grid('SoilMoi100_200cm_tavg')
                self.soil_units = sg.units

            # create new root zone parameters: partials weighted by % of total depth #
            root_zone1 = np.round((soil_00_10 * 0.2) + (soil_10_40 * 0.8), 6)
            root_zone2 = np.round((soil_00_10 * 0.1) + (soil_10_40 * 0.3) + (soil_40_100 * 0.6), 6)
            total_zone = np.round((soil_00_10 * 0.05) + (soil_10_40 * 0.15) + (soil_40_100 * 0.3) + (soil_100_200 * 0.5), 6)

            return np.flipud(root_zone1), np.flipud(root_zone2), np.flipud(total_zone)  # flip arrays to match N-S direction of other data
        except ValueError:
            raise
        except Exception:
            raise

    def create_soil_moisture_file(self, file_name):
        """

        Args:
            file_name:

        Returns:

        """
        raw_file_path = "{}/{}".format(self.__raw_data_dir, file_name)
        file_date = self.__get_fldas_date(file_name)
        output_file = os.path.join(self.__working_dir, "STEP_0104_SM_{}_{}.nc".format(self.__region, file_date))
        output_data_set = None
        try:
            # generate soil moisture parameters #
            root_zone1, root_zone2, total_zone = self.__create_soil_moisture_parameters(raw_file_path)

            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': [self.__get_fldas_calendar_value(file_name)],
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)

            # add soil moisture parameters to output data set #
            root_zone1_var = output_data_set.createVariable('RootZone_SM', 'float32', ('time', 'latitude', 'longitude'))
            root_zone1_var.units = self.soil_units
            root_zone1_var.missing_value = self.__missing
            root_zone1_var.standard_name = "soil_moisture_content"
            root_zone1_var.long_name = "soil moisture content 0cm to 40cm"
            root_zone1_var[0] = root_zone1

            root_zone2_var = output_data_set.createVariable('RootZone2_SM', 'float32', ('time', 'latitude', 'longitude'))
            root_zone2_var.units = self.soil_units
            root_zone2_var.missing_value = self.__missing
            root_zone2_var.standard_name = "soil_moisture_content"
            root_zone2_var.long_name = "soil moisture content 0cm to 100cm"
            root_zone2_var[0] = root_zone2

            total_zone_var = output_data_set.createVariable('TotalColumn_SM', 'float32', ('time', 'latitude', 'longitude'))
            total_zone_var.units = self.soil_units
            total_zone_var.missing_value = self.__missing
            total_zone_var.standard_name = "soil_moisture_content"
            total_zone_var.long_name = "soil moisture content 0cm to 200cm"
            total_zone_var[0] = total_zone
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
        # initialize a new soil moisture class #
        soil_moisture = SoilMoisture()
        # determine the files to process #
        files_to_process = []
        if mode == 'all':
            print("Processing all months.")
            files_to_process = soil_moisture.get_fldas_files_to_process(True)
        else:
            files_to_process = soil_moisture.get_fldas_files_to_process()
            if len(files_to_process) == 0:
                print("All months have been processed for 5km Soil Moisture.")
            else:
                print("Processing needed months for 5km Soil Moisture.")
        # create any SubGrids required for processing #
        for f in files_to_process:
            soil_moisture.create_soil_moisture_file(f)
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
