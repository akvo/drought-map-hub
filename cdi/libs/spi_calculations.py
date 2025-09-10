# -*- coding: utf-8 -*-
import numpy as np
import numpy.ma as ma
import scipy.stats as stats
import warnings


def calculate_monthly_spi(values):
    """
    This function calculates the Standardized Precipitation Index according to
        "CHARACTERISTICS OF 20TH CENTURY DROUGHT IN THE UNITED STATES AT MULTIPLE TIME SCALES"
        by Daniel C. Edwards and Thomas B. McKee
    Args:
        values: numpy 3D array of monthly precipitation values per year in mm/month

    Returns:
        numpy 3D array of monthly SPI values
    """
    warnings.simplefilter("ignore")
    try:
        data_mask = np.where(values == 0.0, 0, 1)
        masked_values = ma.masked_equal(values, 0.0)
        # calculate the â value #
        mean_precip = ma.average(masked_values, axis=0)
        period_log_total = ma.sum(ma.log(masked_values), axis=0)
        period_length = len(values)
        alpha = np.maximum(0.01, ma.log(mean_precip) - (period_log_total / period_length))  # limit to prevent errors
        alpha_hat = np.reciprocal(alpha * 4.0) * (1.0 + ma.sqrt(1.0 + (1.333334 * alpha)))
        # calculate the ß value #
        beta_hat = np.maximum(0.0001, mean_precip / alpha_hat)  # limit to prevent errors
        # calculate the Gamma Cumulative Distribution #
        gamma_cd = stats.gamma.cdf(masked_values, a=alpha_hat, scale=beta_hat)
        # calculate the q value (m/n where m is the sum of zero values and n is the number of years) #
        zero_count = np.sum(np.equal(np.array(values), 0.0), axis=0)
        q_factor = np.clip(zero_count / period_length, 0.0, 1.0)  # q should be between 0.0 and 1.0
        # calculate the cumulative probability H(x) #
        cumulative_prob = q_factor + ((1.0 - q_factor) * gamma_cd)
        # convert to a standard distribution #
        spi_values = stats.norm.ppf(cumulative_prob)
        # cleanup memory #
        del alpha, alpha_hat, beta_hat, gamma_cd, cumulative_prob
        return np.where(data_mask, spi_values, -9999.0)  # mask out no-precipitation areas
    except ValueError:
        raise
    except Exception:
        raise
