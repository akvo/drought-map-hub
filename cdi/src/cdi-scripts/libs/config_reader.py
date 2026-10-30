import json
import os


class ConfigParser:
    """
    This class handles the parsing and "get" calls for the configuration settings
    """
    def __init__(self):
        self.config = {}
        # get the base path of the project #
        base_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        # read the project config settings from the JSON #
        with open(base_path + '/cdi_project_settings.conf', 'r') as fh:
            self.config = json.loads(fh.read())
        # read the directory settings from the JSON #
        with open(base_path + '/cdi_directory_settings.conf', 'r') as fh:
            file_config = json.loads(fh.read())
            for item in file_config.keys():
                self.config[item] = file_config[item]
        # read the file patterns settings from the JSON #
        with open(base_path + '/cdi_pattern_settings.conf', 'r') as fh:
            file_config = json.loads(fh.read())
            for item in file_config.keys():
                self.config[item] = file_config[item]

    def get(self, parameter, option=None):
        """
        This function returns the requested configuration item

        Args:
            parameter (str): The name of the config item to return
            option (str): The name of the sub-option if defined

        Returns:
            The requested configuration setting
        """
        if option is not None:
            return self.config[parameter][option]
        elif parameter == 'latitudes':
            n_lat = int(self.config['bounds']['n_lat'] * 1000.0)
            s_lat = int(self.config['bounds']['s_lat'] * 1000.0)
            latitudes = []
            for lat in range(n_lat, s_lat, -50):
                latitudes.append(round(lat * 0.001, 3))
            latitudes.append(round(self.config['bounds']['s_lat'], 3))
            return latitudes
        elif parameter == 'longitudes':
            w_lon = int(self.config['bounds']['w_lon'] * 1000.0)
            e_lon = int(self.config['bounds']['e_lon'] * 1000.0)
            longitudes = []
            for lon in range(w_lon, e_lon, 50):
                longitudes.append(round(lon * 0.001, 3))
            longitudes.append(round(self.config['bounds']['e_lon'], 3))
            return longitudes
        else:
            return self.config[parameter]
