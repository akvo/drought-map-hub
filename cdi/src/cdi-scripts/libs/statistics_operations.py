import libs.netcdf_functions as netcdf
import numpy as np
import numpy.ma as ma


class StatisticOperations:
    """
    This is the class for computing anomalies and rankings
    """
    def __init__(self):
        self.__missing = -9999.0

    def compute_anomalies_from_files(self, files, parameter):
        """
        This function loads yearly for a particular month, and computes the anomaly per grid point per year
            Anomalies are computed using the delta from the mean, vs. the standard deviation
            For each grid point:
                Anomaly = (monthly value for that year - mean of monthly value for all years) / standard deviation of yearly values
        Args:
            files (List[str]): The month to process per year
            parameter (str): the name of the NetCDF parameter to load

        Returns:
            List of 2D numpy arrays containing the anomaly values
        """
        try:
            month_values = []
            # load the data #
            for f in files:
                data_set = netcdf.open_dataset(f)
                month_values.append(netcdf.extract_data(data_set, parameter, -1))
                data_set.close()
            masked_values = ma.masked_equal(month_values, self.__missing)  # mask out missing data
            mask = np.where(np.mean(month_values, axis=0) == self.__missing, 1, 0)
            # compute the mean delta value #
            month_mean = ma.mean(masked_values, axis=0)
            # masked_mean = ma.masked_equal(month_mean, self.__missing)
            # compute the standard deviation #
            month_std = ma.std(masked_values, axis=0, ddof=1)
            # masked_std = ma.masked_equal(month_std, self.__missing)
            # compute the anomaly for each month #
            anomalies = []
            for values in masked_values:
                month_anomaly = np.ma.true_divide(np.ma.subtract(values, month_mean), month_std)
                masked_anomaly = np.ma.masked_where(mask, month_anomaly.filled(0.0))
                anomalies.append(month_anomaly.filled(self.__missing))
            return anomalies
        except ValueError:
            raise
        except Exception:
            raise

    def compute_anomalies_from_values(self, values):
        """
        This function loads yearly for a particular month, and computes the anomaly per grid point per year
            Anomalies are computed using the delta from the mean, vs. the standard deviation
            For each grid point:
                Anomaly = (monthly value for that year - mean of monthly value for all years) / standard deviation of yearly values
        Args:
            values (List[]): list of numpy 2D arrays

        Returns:
            List of 2D numpy arrays containing the anomaly values
        """
        try:
            month_values = ma.masked_equal(values, self.__missing)  # mask out missing data
            # compute the mean delta value #
            month_mean = ma.average(month_values, axis=0)
            masked_mean = ma.masked_equal(month_mean, self.__missing)
            # compute the standard deviation #
            month_std = ma.std(month_values, axis=0, ddof=1)
            masked_std = ma.masked_equal(month_std, self.__missing)
            # compute the anomaly for each month #
            anomalies = []
            for values in month_values:
                month_anomaly = (values-masked_mean)/masked_std
                masked_anomaly = month_anomaly.filled(self.__missing)
                anomalies.append(masked_anomaly)
            return anomalies
        except ValueError:
            raise
        except Exception:
            raise

    def rank_parameter(self, values):
        """
        This function ranks values over a time period on a 0.0 to 1.0 scale
            This uses a matrix-based version of the mean rank found in the SciPy Stats module
        Args:
            values: 3D numpy array of the values over time for an area

        Returns:
            3D numpy array of the ranked values for the area
        """
        try:
            # mask out missing values #
            masked_values = ma.masked_equal(values, self.__missing)
            # create place-holder for the year grids #
            ranked_data = []
            # loop thru the sets and add the compare counts to the masks #
            for j, base_data in enumerate(masked_values):
                strict_ranks = np.zeros_like(base_data)
                weak_ranks = np.zeros_like(base_data)
                # loop thru again and compare the remaining sets against the base #
                for i, compare_data in enumerate(masked_values):
                    if i != j:  # skip if the same index as the base #
                        # increment the cells based on rank comparison #
                        np.add(strict_ranks, ma.where(base_data > compare_data, 1, 0), out=strict_ranks)
                        np.add(weak_ranks, ma.where(base_data >= compare_data, 1, 0), out=weak_ranks)
                # compute the mean rank #
                ranks = (strict_ranks + weak_ranks) * 0.5
                # append the year to the output #
                ranked_data.append(ranks)
            # divide sum by total years #
            count = np.ma.masked_equal(ma.amax(ranked_data, axis=0) + 1, 0)
            pct_data = np.round(np.ma.true_divide(np.ma.asarray(ranked_data), count), 3)
            final_ranks = np.ma.masked_equal(pct_data, self.__missing)
            return final_ranks
        except ValueError:
            raise
        except Exception:
            raise
