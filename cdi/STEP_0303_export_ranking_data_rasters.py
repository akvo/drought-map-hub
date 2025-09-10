# -*- coding: utf-8 -*-
import os
from libs.config_reader import ConfigParser
from libs.file_operations import FileHandler
import libs.netcdf_functions as netcdf
from argparse import ArgumentParser
import rasterio
from rasterio.transform import Affine
from datetime import datetime, date, timedelta


class NetCDFtoTIFF:
    """
    This is the core processing class for executing GeoTiff export
    """
    def __init__(self, parameter, mode, cdi_date=None):
        self.__parameter = parameter
        self.cdi_date = cdi_date
        self.__config = ConfigParser()
        self.__mode = mode
        self.__cdi_weights = self.__config.get('cdi_parameters', 'weights')

    def __enter__(self):
        if self.__parameter == 'cdi' or self.__cdi_weights[self.__parameter] > 0:
            print("Exporting Tiff(s) for {}...".format(self.__parameter.upper()))
            self.__working_dir = self.__config.get('geotiff_dir').replace("\\", '/') + '/' + self.__parameter.upper()
            self.__output_dir = self.__config.get('output_dir').replace("\\", '/')
            self.__region = self.__config.get('region_name')
            self.__bounds = self.__config.get('bounds')
            self.__latitudes = self.__config.get('latitudes')
            self.__longitudes = self.__config.get('longitudes')
            self.__rows = len(self.__latitudes)
            self.__cols = len(self.__longitudes)
            self.__file_patterns = self.__config.get('file_patterns')
            self.__fileHandler = FileHandler(
                raw_data_dir=None,
                working_dir=self.__working_dir,
                file_patterns=self.__file_patterns
            )
            self.__times = None
            self.__data = None
            self.__transform = None
            self.__projection = '+proj=latlong'
            self.__missing = -9999.0
            # load the time(s) and data #
            self.__get_data()
            # get the transformation #
            self.__get_transformation()
            # export the image(s) #
            self.__export_geotiffs()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__times = None
        self.__data = None

    def __get_data(self):
        """
        This function loads the applicable time(s) and data array(s) from the appropriate NetCDF file
            containing the CDI input or ranked sum
        Returns:
            None: results are stored directly in the class instance
        """
        input_data_set = None
        # define the available file names for the sources #
        input_files = {
            "lst": os.path.join(self.__output_dir, "STEP_0201_LST_anomaly_pct_rank_{}.nc".format(self.__region)),
            "ndvi": os.path.join(self.__output_dir, "STEP_0202_NDVI_anomaly_pct_rank_{}.nc".format(self.__region)),
            "spi": os.path.join(self.__output_dir, "STEP_0203_SPI_anomaly_pct_rank_{}.nc".format(self.__region)),
            "sm": os.path.join(self.__output_dir, "STEP_0204_SM_pct_rank_{}.nc".format(self.__region)),
            "cdi": os.path.join(self.__output_dir, "STEP_0302_CDI_pct_rank_{}.nc".format(self.__region))
        }
        # define the NetCDF parameter names for each source #
        input_parameters = self.__config.get('cdi_parameters', 'names')
        input_parameters['cdi'] = "cdi_wt_sum_pr"
        # extract the time(s) and data #
        try:
            source = input_files[self.__parameter]
            source_parameter = input_parameters[self.__parameter]
            input_data_set = netcdf.open_dataset(source)
            if self.__mode == 'all':
                self.__times = input_data_set.variables['time'][:]
                self.__data = netcdf.extract_data(input_data_set, source_parameter, -1)
            else:
                all_times = input_data_set.variables['time'][:]
                last = len(all_times) - 1
                if self.cdi_date is not None:
                    for idx, d in enumerate(all_times):
                        # set the index to use to the matching CDI date #
                        if d == self.cdi_date:
                            last = idx
                else:
                    # update the last CDI date for the 'latest' mode #
                    self.cdi_date = all_times[last]
                # extract the data for the last CDI month #
                self.__times = [all_times[last]]
                self.__data = [netcdf.extract_data(input_data_set, source_parameter, last)]

        except IOError:
            raise
        except Exception:
            raise
        finally:
            if input_data_set is not None:
                input_data_set.close()

    def __get_transformation(self):
        res = 0.05
        try:
            self.__transform = Affine.translation(self.__longitudes[0] - res / 2, self.__latitudes[0] + res / 2) * Affine.scale(res, -res)
        except ValueError:
            raise
        except Exception:
            raise

    @staticmethod
    def create_date_string(time):
        """
        This function converts the NetCDF days since Jan 1, 1990 to a date string
        Args:
            time: the NetCDF time

        Returns:
            String of the year/month in 'YYMM' format
        """
        origin_date = date(1900, 1, 1)
        data_date = origin_date + timedelta(days=time)
        return data_date.strftime('%Y%m')

    def __export_geotiffs(self):
        """
        This function takes the loaded NetCDF data and generates a GeoTiff image for each date requested
        Returns:
            None
        """
        output = None
        try:
            # loop thru times and generate a GeoTiff for each date #
            for t, time in enumerate(self.__times):
                date_str = self.create_date_string(int(time))
                filename = os.path.join(self.__working_dir, "STEP_0303_{}_pct_rank_{}_{}.tif".format(self.__parameter.upper(), self.__region, date_str))
                # create new GeoTiff #
                output = rasterio.open(
                    filename,
                    'w',
                    driver='GTiff',
                    width=self.__cols,
                    height=self.__rows,
                    count=1,
                    dtype=rasterio.float32,
                    crs=self.__projection,
                    transform=self.__transform
                )
                # write the data to the image #
                output.write(self.__data[t].astype(rasterio.float32), 1)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output is not None:
                output.close()


def main(args):
    """
    This is the main entry point for the program
    """
    mode = str(args.mode)
    script_start = datetime.now()
    try:
        # set the list of parameters to convert: cdi must be first #
        parameters = ["cdi", "lst", "ndvi", "spi", "sm"]
        cdi_date = None
        for p in parameters:
            # initialize a new TIFF export class #
            with NetCDFtoTIFF(p, mode, cdi_date) as tif_exporter:
                if cdi_date is None:
                    cdi_date = tif_exporter.cdi_date
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
                        help="The times to export: latest or all. Default is updates")
    # execute the program with the supplied option
    main(parser.parse_args())
