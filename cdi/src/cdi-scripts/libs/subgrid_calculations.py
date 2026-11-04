import numpy as np


class NetCDFSubGrid:
    import libs.netcdf_functions as NetCDF

    def __init__(self, aoi, file_path, interpolate=False):
        self.__aoi = aoi
        self.__file_path = file_path
        self.interpolate = interpolate
        self.__dataset = None
        # initialize class properties #
        self.__missing = np.float32(-9999.0)
        self.units = ""
        self.first_root_x = 0
        self.last_root_x = 0
        self.first_root_y = 0
        self.last_root_y = 0
        self.columns = int(abs(aoi['e_lon'] - aoi['w_lon']) * 20) + 1  # 0.05 degree spacing = 20 columns/degree
        self.rows = int(round(abs(aoi['n_lat'] - aoi['s_lat']) * 20, 0) + 1)  # 0.05 degree spacing = 20 rows/degree
        
    def __enter__(self):
        try:
            self.__dataset = self.NetCDF.open_dataset(self.__file_path)
            # get the dimensions of the source data #
            self.__root_dimensions = self.NetCDF.get_dimensions(self.__dataset)
            # determine the bounding box that covers the Area of Interest (aoi)
            if self.interpolate:
                self.__compute_bounding_box()
            else:
                self.__bounds = self.__aoi
            # determine the properties of the SubGrid area #
            self.__compute_indices(self.__bounds, self.__root_dimensions['latitudes'], self.__root_dimensions['longitudes'])
            return self
        except IOError:
            raise
        except Exception:
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__dataset is not None:
            self.__dataset.close()

    def __compute_bounding_box(self):
        """
        This function determines the 1.0deg area that covers our target 0.5deg AOI
        """
        # round the west longitude down to the nearest 0.1 degree, and shift by 0.05 degrees #
        w_lon = round(round(self.__aoi['w_lon'], 1) - 0.05, 2)
        # round the east longitude up to the nearest 0.1 degree, and shift by 0.05 degrees #
        e_lon = round(round(self.__aoi['e_lon'], 1) + 0.05, 2)
        # round the north latitude down to the nearest 0.1 degree, and shift by 0.05 degrees #
        n_lat = round(round(self.__aoi['n_lat'], 1) + 0.05, 2)
        # round the south latitude down to the nearest 0.1 degree, and shift by 0.05 degrees #
        s_lat = round(round(self.__aoi['s_lat'], 1) - 0.05, 2)
        # set the bounding box of the raw data #
        self.__bounds = {'w_lon': w_lon, 'e_lon': e_lon, 'n_lat': n_lat, 's_lat': s_lat}
        """
        Since the interpolation computes the SubGrid values in a pattern of 2x2 blocks,
            the data we are interested in may be a subset of the interpolated data
        """
        # compute the SubGrid corners #
        start_y = s_lat + 0.025  # the SubGrid points are 0.025 degrees offset from the original points
        self.start_y = int((self.__aoi['s_lat'] - start_y) * 20)
        self.end_y = int(self.start_y + self.rows)
        start_x = w_lon + 0.025  # the SubGrid points are 0.025 degrees offset from the original points
        self.start_x = int((self.__aoi['w_lon'] - start_x) * 20)
        self.end_x = int(self.start_x + self.columns)

    def __compute_indices(self, bounds, latitudes, longitudes):
        """
        This function determines the index range of the latitude and longitude arrays
            that fits the area of interest (SubGrid)
        Example:
            Given a global grid at 0.5 degree spacing that starts at -179.75, -89.75
                There are 720 longitude values and 360 latitude values
                Note the 0.25 degree offset for the center of the grid "boxes"
            If we are interested in an area that covers -50.0, -30.0 to 50.0, 30.0, then our bounds are:
                -49.75, -29.75 to 49.75 to 29.75
                For the longitudes:
                    -49.75 is 130 degrees to the east of -179.75 (array position 0), so our starting index is 260
                    49.75 is 229.5 degrees to the east of -179.75, so our ending index is 459
                For the latitudes:
                    -29.75 is 60 degrees to the north of -89.75, so the starting index is 120
                    29.75 is 119.5 degrees north of -89.75, so the ending index is 239
        Args:
            bounds (dictionary): object containing the coordinates of the Area of Interest
            latitudes (list of floats): latitude values of the original grid
            longitudes (list of floats): longitude values of the original grid

        Returns:
            None: adds values to class properties
        """
        # find the range for the latitudes of the subset #
        for j, y in enumerate(latitudes):
            if y == bounds['s_lat']:
                self.first_root_y = j
            elif y == bounds['n_lat']:
                self.last_root_y = j + 1  # ensure we have coverage if the subset is offset by 1 cell
        # find the range for the longitudes of the subset #
        for i, x in enumerate(longitudes):
            if x == bounds['w_lon']:
                self.first_root_x = i
            elif x == bounds['e_lon']:
                self.last_root_x = i + 1  # ensure we have coverage if the subset is offset by 1 cell
        # set span of the raw data subset #
        self.root_rows = int(self.last_root_y - self.first_root_y)
        self.root_columns = int(self.last_root_x - self.first_root_x)

    def __extract_raw_subset(self, parameter):
        """
        This function extracts a subset of data from the requested parameter using the computed cells required to cover the current Area of Interest
        Args:
            parameter (str): the NetCDF parameter name

        Returns:
            2D numpy array of floats for the subset area
        """
        if 'times' in self.__root_dimensions:
            full_data = self.NetCDF.extract_data(self.__dataset, parameter)
        else:
            full_data = self.NetCDF.extract_data(self.__dataset, parameter, -1)
        return full_data[self.first_root_y: self.last_root_y, self.first_root_x: self.last_root_x]

    def __interpolate_cells(self, raw_data):
        """
        This function takes values from the original data that cover the supplied bounds,
            and then interpolates the data to 0.05 degree spacing
        The new data values are created using a special form of bilinear-interpolation where the empty cells
            (represented by the value -9999.0) are not included in the weighting
        Args:
            raw_data (2D numpy array of floats): the original data to process

        Returns:
            2D numpy array (floats) of the interpolated data covering the Area of Interest (bounds)
        """
        # initialize output array with a 4 cell buffer #
        output_data = np.full((self.rows + 4, self.columns + 4), self.__missing, dtype='float')
        # pre-define the weight patterns: 16ths of the raw values to use #
        w_jj_ii = np.array([[0.5625, 0.1875], [0.1875, 0.0625]])  # 9, 3, 3, 1
        w_jj_ip = np.array([[0.1875, 0.5625], [0.0625, 0.1875]])  # 3, 9, 1, 3
        w_jp_ii = np.array([[0.1875, 0.0625], [0.5625, 0.1875]])  # 3, 1, 9, 3
        w_jp_ip = np.array([[0.0625, 0.1875], [0.1875, 0.5625]])  # 1, 3, 3, 9

        def __interpolate_cell(values, weights, mask):
            """
            Private function that interpolates a cell based on the distance to the original cells,
                and if the original cells contain non-missing values
            Args:
                values (2D numpy array of floats): subset of the original data that affects the new cell
                weights (2D numpy array of floats): predetermined weighting of the original data
                mask (2D numpy array of floats): array of zeros and ones representing False/True if an original data
                    cell should be used in the interpolation

            Returns:
                float value of the interpolated data for the target cell
            """
            # determine the scale factor for the weights which accounts for empty cells
            scale = np.true_divide(1.0, np.sum(mask * weights))
            # return the interpolated value: sum of the raw values multiplied by their weights
            return np.sum(values * (weights * mask) * scale)

        # start to process the bilinear interpolation #
        last_root_j = self.root_rows - 1  # last column in original data (minus 1 offset for zero-based array)
        last_root_i = self.root_columns - 1  # last column in original data (minus 1 offset for zero-based array)
        # iterate by row #
        for jj in range(0, last_root_j):
            # set row indices for new grid points #
            j1 = jj * 2
            j2 = jj * 2 + 1
            jp = jj + 1
            # iterate by column #
            for ii in range(0, last_root_i):
                # set column indices for new grid points #
                i1 = ii * 2
                i2 = ii * 2 + 1
                ip = ii + 1
                # bilinear interpolation of the interior #
                data_subset = np.array([[raw_data[jj][ii], raw_data[jj][ip]], [raw_data[jp][ii], raw_data[jp][ip]]])
                weight_mask = np.where(data_subset == self.__missing, 0, 1)
                if np.sum(weight_mask) > 0:
                    output_data[j1][i1] = __interpolate_cell(data_subset, w_jj_ii, weight_mask)
                    output_data[j1][i2] = __interpolate_cell(data_subset, w_jj_ip, weight_mask)
                    output_data[j2][i1] = __interpolate_cell(data_subset, w_jp_ii, weight_mask)
                    output_data[j2][i2] = __interpolate_cell(data_subset, w_jp_ip, weight_mask)
        return output_data

    def create_sub_grid(self, parameter):
        """
        This function creates a new numpy array for the current Area of Interest interpolated to the target resolution of 0.05 degrees
        Args:
            parameter (str): the NetCDF parameter name

        Returns:
            2D numpy array of floats
        """
        # load the subset of the raw data to interpolate #
        raw_data = self.__extract_raw_subset(parameter)
        # set the current units #
        self.units = self.NetCDF.get_parameter_units(self.__dataset, parameter)
        if self.interpolate:
            # interpolate the data #
            interpolated_data = self.__interpolate_cells(raw_data)
            # return the interpolated data in our Area of Interest #
            results = interpolated_data[self.start_y: self.end_y, self.start_x: self.end_x]
        else:
            results = raw_data
        return results


class HDFSubGrid:
    import libs.hdf_functions as HDF

    def __init__(self, aoi, file_path, group):
        self.__bounds = aoi
        self.__file_path = file_path
        self.__dataset = None
        self.__group = group
        # initialize class properties #
        self.__missing = np.float32(-9999.0)
        self.units = ""
        self.first_root_x = 0
        self.last_root_x = 0
        self.first_root_y = 0
        self.last_root_y = 0
        self.columns = int(abs(aoi['e_lon'] - aoi['w_lon']) * 20) + 1  # 0.05 degree spacing = 20 columns/degree
        self.rows = int(abs(aoi['n_lat'] - aoi['s_lat']) * 20) + 1  # 0.05 degree spacing = 20 rows/degree

    def __enter__(self):
        try:
            self.__dataset = self.HDF.open_dataset(self.__file_path)
            # set the dimensions of the source data #
            self.__root_latitudes = np.arange(89.975, -90.05, -0.05)
            self.__root_longitudes = np.arange(-179.975, 180.05, 0.05)
            # determine the properties of the SubGrid area #
            self.__compute_indices(self.__bounds, self.__root_latitudes, self.__root_longitudes)
            return self
        except IOError:
            raise
        except Exception:
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__dataset is not None:
            self.__dataset.close()

    def __compute_indices(self, bounds, latitudes, longitudes):
        """
        This function determines the index range of the latitude and longitude arrays
            that fits the area of interest (SubGrid)
        Example:
            Given a global grid at 0.5 degree spacing that starts at -179.75, -89.75
                There are 720 longitude values and 360 latitude values
                Note the 0.25 degree offset for the center of the grid "boxes"
            If we are interested in an area that covers -50.0, -30.0 to 50.0, 30.0, then our bounds are:
                -49.75, -29.75 to 49.75 to 29.75
                For the longitudes:
                    -49.75 is 130 degrees to the east of -179.75 (array position 0), so our starting index is 260
                    49.75 is 229.5 degrees to the east of -179.75, so our ending index is 459
                For the latitudes:
                    -29.75 is 60 degrees to the north of -89.75, so the starting index is 120
                    29.75 is 119.5 degrees north of -89.75, so the ending index is 239
        Args:
            bounds (dictionary): object containing the coordinates of the Area of Interest
            latitudes (numpy array of floats): latitude values of the original grid
            longitudes (numpy array of floats): longitude values of the original grid

        Returns:
            None: adds values to class properties
        """
        # find the range for the latitudes of the subset #
        for j, y in enumerate(latitudes):
            if round(y, 3) == float(bounds['n_lat']):
                self.first_root_y = j
            elif round(y, 3) == float(bounds['s_lat']):
                self.last_root_y = j + 1  # ensure we have coverage
        # find the range for the longitudes of the subset #
        for i, x in enumerate(longitudes):
            if round(x, 3) == float(bounds['w_lon']):
                self.first_root_x = i
            elif round(x, 3) == float(bounds['e_lon']):
                self.last_root_x = i + 1  # ensure we have coverage

    def __extract_raw_subset(self, parameter):
        """
        This function extracts a subset of data from the requested parameter using the computed cells required to cover the current Area of Interest
        Args:
            parameter (str): the HDF parameter name

        Returns:
            2D numpy array of floats for the subset area
        """
        full_data = self.HDF.extract_data(self.__dataset, self.__group, parameter, -1)
        return full_data[self.first_root_y: self.last_root_y, self.first_root_x: self.last_root_x]

    def create_sub_grid(self, parameter):
        """
        This function creates a new numpy array for the current Area of Interest
            Note: This function can be expanded in the future if we need to interpolate the HDF data to a finer resolution
        Args:
            parameter (str): the HDF parameter name

        Returns:
            2D numpy array of floats
        """
        # load the subset of the raw data #
        subset = self.__extract_raw_subset(parameter)
        return subset


class CHIRPSSubGrid:
    import imageio

    def __init__(self, aoi, file_path):
        self.__bounds = aoi
        self.__file_path = file_path
        self.__dataset = None
        # initialize class properties #
        self.__missing = np.float32(-9999.0)
        self.units = ""
        self.first_root_x = 0
        self.last_root_x = 0
        self.first_root_y = 0
        self.last_root_y = 0
        self.columns = int(abs(aoi['e_lon'] - aoi['w_lon']) * 20) + 1  # 0.05 degree spacing = 20 columns/degree
        self.rows = int(abs(aoi['n_lat'] - aoi['s_lat']) * 20) + 1  # 0.05 degree spacing = 20 rows/degree

    def __enter__(self):
        try:
            self.__dataset = self.imageio.imread(self.__file_path)
            # set the dimensions of the source data #
            self.__root_latitudes = np.arange(49.975, -50.05, -0.05)
            self.__root_longitudes = np.arange(-179.975, 180.05, 0.05)
            # determine the properties of the SubGrid area #
            self.__compute_indices(self.__bounds, self.__root_latitudes, self.__root_longitudes)
            return self
        except IOError:
            raise
        except Exception:
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__dataset is not None:
            self.__dataset = None

    def __compute_indices(self, bounds, latitudes, longitudes):
        """
        This function determines the index range of the latitude and longitude arrays
            that fits the area of interest (SubGrid)
        Example:
            Given a global grid at 0.5 degree spacing that starts at -179.75, -89.75
                There are 720 longitude values and 360 latitude values
                Note the 0.25 degree offset for the center of the grid "boxes"
            If we are interested in an area that covers -50.0, -30.0 to 50.0, 30.0, then our bounds are:
                -49.75, -29.75 to 49.75 to 29.75
                For the longitudes:
                    -49.75 is 130 degrees to the east of -179.75 (array position 0), so our starting index is 260
                    49.75 is 229.5 degrees to the east of -179.75, so our ending index is 459
                For the latitudes:
                    -29.75 is 60 degrees to the north of -89.75, so the starting index is 120
                    29.75 is 119.5 degrees north of -89.75, so the ending index is 239
        Args:
            bounds (dictionary): object containing the coordinates of the Area of Interest
            latitudes (numpy array of floats): latitude values of the original grid
            longitudes (numpy array of floats): longitude values of the original grid

        Returns:
            None: adds values to class properties
        """
        # find the range for the latitudes of the subset #
        for j, y in enumerate(latitudes):
            if round(y, 3) == float(bounds['n_lat']):
                self.first_root_y = j
            elif round(y, 3) == float(bounds['s_lat']):
                self.last_root_y = j + 1  # ensure we have coverage
        # find the range for the longitudes of the subset #
        for i, x in enumerate(longitudes):
            if round(x, 3) == float(bounds['w_lon']):
                self.first_root_x = i
            elif round(x, 3) == float(bounds['e_lon']):
                self.last_root_x = i + 1  # ensure we have coverage

    def create_sub_grid(self):
        """
        This function creates a new numpy array for the current Area of Interest
            Note: This function can be expanded in the future if we need to interpolate the TIF data to a finer resolution
        Returns:
            2D numpy array of floats
        """
        # load the subset of the raw data #
        data = np.array(self.__dataset)
        subset = data[self.first_root_y: self.last_root_y, self.first_root_x: self.last_root_x]
        return subset
