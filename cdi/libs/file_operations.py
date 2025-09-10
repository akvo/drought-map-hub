import os
import re


class FileHandler:
    def __init__(self, **kwargs):
        self.__raw_data_dir = kwargs['raw_data_dir']
        self.__working_dir = kwargs['working_dir']
        self.__patterns = kwargs['file_patterns']
        self.__validate_directories()

    def __validate_directories(self):
        """
        This function checks if the required directories exist, and creates the temporary directory if needed
        """
        # check the raw data directory #
        if self.__raw_data_dir is not None and not os.path.isdir(self.__raw_data_dir):
            raise IOError("Supplied raw data directory does not exist: '{}'".format(self.__raw_data_dir))

        # check the working data directory #
        if not os.path.isdir(self.__working_dir):
            try:
                print("Creating working data directory.")
                os.mkdir(self.__working_dir)
            except IOError:
                print("Error creating working directory; check permissions on parent directory.")

    def get_raw_file_names(self, pattern, root=None, subdir=None):
        """
        This function reads the raw data directory to find available files to process

        Args:
            pattern (str): name of the file pattern (from the config) to use in the search
            root (str): root directory to scan
            subdir (str): name of the sub-directory if being used
        Returns:
            List of file names
        """
        results = []
        if root is None:
            root = self.__raw_data_dir
        try:
            # get the list fo files in the raw data directory #
            for f in os.listdir(root):
                # check if we have a sub-directory #
                full_path = os.path.join(root, f)
                if os.path.isdir(full_path):
                    results = results + self.get_raw_file_names(pattern, full_path, f)
                # test the file name against the pattern #
                if re.search(r'{}'.format(self.__patterns[pattern]), f):
                    # append the name to the results list #
                    if root != self.__raw_data_dir:
                        results.append('{}/{}'.format(subdir, f))
                    else:
                        results.append(str(f))
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return results

    def get_working_file_names(self, pattern):
        """
        This function reads the working data directory to find processed files

        Args:
            pattern (str): name of the file pattern (from the config) to use in the search
        Returns:
            List of file names
        """
        results = []
        try:
            # get the list fo files in the raw data directory #
            for f in os.listdir(self.__working_dir):
                # test the file name against the pattern #
                if re.search(r'{}'.format(self.__patterns[pattern]), f):
                    # append the name to the results list #
                    results.append(str(f))
        except IOError:
            raise
        except Exception:
            raise
        finally:
            return results
