# -*- coding: utf-8 -*-
import os
from libs.config_reader import ConfigParser
from libs.file_operations import FileHandler
from libs.statistics_operations import StatisticOperations
import libs.netcdf_functions as netcdf
import numpy as np
import re
from datetime import datetime, date


class SoilMoistureRanking:
    """
    This is the core processing class for executing all soil moisture ranking operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__stats = StatisticOperations()
        self.__working_dir = self.__config.get('scratch_dir').replace("\\", '/') + '/SM'
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__file_patterns = self.__config.get('file_patterns')
        self.__file_patterns['sm_netcdf_regex'] = "STEP_0104_SM_{}_((?:19|20)\\d\\d)(0[1-9]|1[0-2])\\.nc".format(self.__region)
        self.__fileHandler = FileHandler(
            raw_data_dir=None,
            working_dir=self.__working_dir,
            file_patterns=self.__file_patterns
        )
        self.__working_file_match = re.compile(r'{}'.format(self.__file_patterns['sm_netcdf_regex']))
        self.__netcdf_files = []
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__times = []
        self.__missing = -9999.0
        self.moisture_data = {}
        # initialize the output file and prepare internal value lists #
        self.__initialize_ranking_file()

    def __get_calendar_times(self):
        """
        This function builds a list of the valid times as days since Jan 1, 1900

        Returns:
            List (floats) of the valid times as number of days since Jan 1, 1900
        """
        origin_date = date(1900, 1, 1)
        times = []
        for f in self.__netcdf_files:
            (year, month) = self.__working_file_match.match(f).groups()
            test_date = date(int(year), int(month), 1)
            time_delta = test_date - origin_date
            times.append(float(time_delta.days))
        return times

    def __get_moisture_files_by_month(self, month):
        """
        This function reads the working data directory to find available files to process by month
        Returns:
            List of fully-qualified names
        """
        results = []
        try:
            test_pattern = self.__file_patterns['sm_netcdf_regex'].split('(0')[0] + str(month) + "\\.nc"
            file_test = re.compile(r'{}'.format(test_pattern))

            results = [
                '{}/{}'.format(self.__working_dir, f) for f in os.listdir(self.__working_dir)
                if file_test.match(f)
            ]
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            return results

    def __initialize_ranking_file(self):
        self.__output_file = os.path.join(self.__output_dir, "STEP_0204_SM_pct_rank_{}.nc".format(self.__region))
        output_data_set = None
        try:
            # get a sorted list of the NetCDF files #
            self.__netcdf_files = sorted(self.__fileHandler.get_working_file_names('sm_netcdf_regex'))
            # get the list of valid times #
            self.__times = self.__get_calendar_times()
            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__times,
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(self.__output_file, out_properties)

            # variables #
            root_zone_rank = output_data_set.createVariable('RootZone_SM_pct_rank', 'float32', ('time', 'latitude', 'longitude'))
            root_zone_rank.units = '1'
            root_zone_rank.missing_value = self.__missing
            root_zone_rank.standard_name = "root_zone_sm_pct_rank"
            root_zone_rank.long_name = "percent ranked root zone soil moisture"

            root_zone2_rank = output_data_set.createVariable('RootZone2_SM_pct_rank', 'float32', ('time', 'latitude', 'longitude'))
            root_zone2_rank.units = '1'
            root_zone2_rank.missing_value = self.__missing
            root_zone2_rank.standard_name = "root_zone2_sm_pct_rank"
            root_zone2_rank.long_name = "percent ranked root zone2 soil moisture"

            total_column_rank = output_data_set.createVariable('TotalColumn_SM_pct_rank', 'float32', ('time', 'latitude', 'longitude'))
            total_column_rank.units = '1'
            total_column_rank.missing_value = self.__missing
            total_column_rank.standard_name = "total_column_sm_pct_rank"
            total_column_rank.long_name = "percent ranked total column soil moisture"
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def get_month_order(self):
        month_list = []
        try:
            # determine the order of the months by checking the first 12 sorted file names #
            for m in range(0, 12):
                null, month = self.__working_file_match.match(self.__netcdf_files[m]).groups()
                month_list.append(month)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return month_list

    def load_soil_moisture_data(self, month):
        try:
            files = self.__get_moisture_files_by_month(month)
            # set the placeholder arrays #
            self.moisture_data['RootZone_SM'] = []
            self.moisture_data['RootZone2_SM'] = []
            self.moisture_data['TotalColumn_SM'] = []

            for f in files:
                data_set = netcdf.open_dataset(f)
                # get root zone values #
                self.moisture_data['RootZone_SM'].append(netcdf.extract_data(data_set, 'RootZone_SM'))
                # get root zone values #
                self.moisture_data['RootZone2_SM'].append(netcdf.extract_data(data_set, 'RootZone2_SM'))
                # get root zone values #
                self.moisture_data['TotalColumn_SM'].append(netcdf.extract_data(data_set, 'TotalColumn_SM'))
                # close data file #
                data_set.close()
        except IOError:
            raise
        except Exception:
            raise

    def rank_parameter(self, parameter, index):
        output_data_set = None
        out_parameter = '{}_pct_rank'.format(parameter)
        try:
            ranked_data = self.__stats.rank_parameter(self.moisture_data[parameter])
            # open file for appending #
            output_data_set = netcdf.open_dataset(self.__output_file, 'a')
            # loop thru the years and set the data to the correct time index #
            for y in range(0, len(ranked_data)):
                output_data_set.variables[out_parameter][index] = ranked_data[y]
                index += 12
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
        rankings = SoilMoistureRanking()
        # loop thru the months and rank the three soil moisture parameters #
        for index, month in enumerate(rankings.get_month_order()):
            print("Ranking data for month: {}".format(month))
            # load data #
            rankings.load_soil_moisture_data(month)

            # rank root zone data #
            rankings.rank_parameter('RootZone_SM', index)

            # rank root zone2 data #
            rankings.rank_parameter('RootZone2_SM', index)

            # rank total column data #
            rankings.rank_parameter('TotalColumn_SM', index)
    except IOError as ioe:
        print(ioe)
    except Exception as ex:
        print(ex)
    finally:
        script_end = datetime.now()
        print("Script execution: {}".format(script_end - script_start))


if __name__ == '__main__':
    main()
