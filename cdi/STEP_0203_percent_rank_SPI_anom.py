# -*- coding: utf-8 -*-
import os
from libs.config_reader import ConfigParser
from libs.statistics_operations import StatisticOperations
import libs.netcdf_functions as netcdf
import numpy as np
from datetime import datetime


class StandardizedPrecipitationIndexRanking:
    """
    This is the core processing class for executing all SPI (standardized precipitation index) ranking operations
    """
    def __init__(self):
        self.__config = ConfigParser()
        self.__stats = StatisticOperations()
        self.__spi_periods = sorted(self.__config.get('spi_periods'))
        self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
        self.__region = self.__config.get('region_name')
        self.__bounds = self.__config.get('bounds')
        self.__input_file = os.path.join(self.__output_dir, "STEP_0103_SPI_anomaly_{}.nc".format(self.__region))
        self.__input_data_set = netcdf.open_dataset(self.__input_file)
        self.__latitudes = self.__config.get('latitudes')
        self.__longitudes = self.__config.get('longitudes')
        self.__times = self.__input_data_set.variables['time'][:]
        self.__number_of_months = len(self.__times)
        self.__missing = -9999.0
        self.__rows = len(self.__latitudes)
        self.__columns = len(self.__longitudes)
        self.__empty_set = np.full((self.__rows, self.__columns), self.__missing)
        # initialize the output file and prepare internal value lists #
        self.__initialize_ranking_file()

    def __initialize_ranking_file(self):
        """
        This function creates the NetCDF file to hold the percent-ranked SPI anomaly data
        Returns:
            None: File is initialized and referenced in the class
        """
        self.__output_file = os.path.join(self.__output_dir, "STEP_0203_SPI_anomaly_pct_rank_{}.nc".format(self.__region))
        output_data_set = None
        try:
            # create the output file #
            out_properties = {
                'latitudes': self.__latitudes,
                'longitudes': self.__longitudes,
                'times': self.__times,
                'time_units': 'days since 1900-01-01 00:00:00.0 UTC'
            }
            output_data_set = netcdf.initialize_dataset(self.__output_file, out_properties)

            # variables #
            for p in self.__spi_periods:
                lst_rank = output_data_set.createVariable('spi_{}_anom_pct_rank'.format(p), 'float32', ('time', 'latitude', 'longitude'))
                lst_rank.units = '1'
                lst_rank.missing_value = self.__missing
                lst_rank.standard_name = "spi_{}_anom_pct_rank".format(p)
                lst_rank.long_name = "percent ranked SPI anomaly"
        except IOError as ioe:
            print(ioe)
        except Exception as ex:
            print(ex)
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def __rank_parameter(self, period, index):
        """
        This function executes the statistical ranking for a particular parameter and month from the SPI values.
            The data is written to the out NetCDF file
        Args:
            period (int): the value of the monthly total period of precipitation used (e.g. 9-month totals to represent a month)
            index (int): the 0-11 index value of the month to rank

        Returns:
            None: data is directly written to the output file
        """
        output_data_set = None
        try:
            # open file for appending #
            output_data_set = netcdf.open_dataset(self.__output_file, 'a')
            # determine the number of years for the month #
            years = int(self.__number_of_months / 12)
            if index < (self.__number_of_months % 12):
                years += 1
            # load the data for the current month #
            data = []
            t = index  # set the input time to the starting index
            valid_index = index
            for y in range(0, years):
                values = netcdf.extract_data(self.__input_data_set, 'spi_{}_anom'.format(period), t)
                if np.amax(values) > self.__missing:  # append the data for ranking
                    data.append(values)
                else:  # set the output data to missing, and skip to the next year
                    output_data_set.variables['spi_{}_anom_pct_rank'.format(period)][t] = self.__empty_set
                    valid_index += 12
                t += 12  # increment by 1 year
            # rank the data by year #
            ranked_data = self.__stats.rank_parameter(data)
            # loop thru the years and set the data to the correct time index #
            t = valid_index
            for y in range(0, len(ranked_data)):
                output_data_set.variables['spi_{}_anom_pct_rank'.format(period)][t] = ranked_data[y]
                t += 12
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()

    def rank_spi_parameters(self):
        """
        This function serves as a wrapper to execute the ranking for all 12 months
        Returns:
            None
        """
        # loop thru the parameters in the SPI anomaly file #
        for p in self.__spi_periods:
            # rank each month series #
            for index in range(0, 12):
                self.__rank_parameter(p, index)
            print("-- SPI anomalies ranked for {}-month totals".format(p))


def main():
    """
    This is the main entry point for the program
    """
    script_start = datetime.now()
    try:
        # initialize a new soil moisture class #
        rankings = StandardizedPrecipitationIndexRanking()
        # loop thru the months and rank the SPI anomalies #
        print("Ranking SPI anomaly data...")
        rankings.rank_spi_parameters()
    except IOError as ioe:
        print(ioe)
    except Exception as ex:
        print(ex)
    finally:
        script_end = datetime.now()
        print("Script execution: {}".format(script_end - script_start))


if __name__ == '__main__':
    main()
