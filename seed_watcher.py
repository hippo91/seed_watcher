#!/usr/bin/env python3
"""
This program retrieves some informations on a seed box
"""
import asyncio
from contextlib import contextmanager
import json
from functools import partial
import os
import sys
from typing import Mapping, Union, Optional, Generator, List
from aiohttp.client_exceptions import ClientConnectorError

from src.localization import BlinkingLocalization, check_licit_ip
from src.transmission import BlinkingDownloadSpeed, get_transmision_session_stats
from src.raspberry import ON_PI, initialize_gpio, cleanup


ConfigurationValues = Union[int, float, List[str]]
ConfigurationMapping = Mapping[str, ConfigurationValues]


def read_config() -> Optional[ConfigurationMapping]:
    """
    Read the configuration file and return a dict
    """
    try:
        with open("config.json", 'r') as conf_file:
            data: ConfigurationMapping = json.load(conf_file)
    except FileNotFoundError:
        return None
    return data


class ConfigurationReader:  # pylint:disable=too-few-public-methods
    """
    This class ensures that the configuration has been read successfully
    """
    def __init__(self, configuration: ConfigurationMapping):
        self.message = ""
        self.is_ok = True
        self.config = configuration

    def get_safe(self, parameter: str) -> Optional[ConfigurationValues]:
        """
        Check if the parameter is in the configuration.
        If it is in then return the value. Else adds a message to the buffer

        :param parameter: parameter to check
        """
        try:
            return self.config[parameter]
        except KeyError:
            self.message += f"The parameter '{parameter}' has not been found!"
            self.message += os.linesep
            self.is_ok = False
            return None


@contextmanager
def configuration_reader(configuration: ConfigurationMapping) -> Generator[ConfigurationReader, None, None]:  # pylint: disable=line-too-long
    """
    This context manager give access to an instance of ConfigurationReader
    class that checks the configuration has been successfully read.
    """
    conf_state = ConfigurationReader(configuration)
    yield conf_state
    if not conf_state.is_ok:
        print("Error! The configuration file is not well formed!",
              file=sys.stderr)
        print(conf_state.message, file=sys.stderr)
        sys.exit(2)


async def main():
    """
    Main function
    """
    conf = read_config()
    if not conf:
        print("Error! "
              "The configuration file (config.json) has not been found!",
              file=sys.stderr)
        sys.exit(1)

    with configuration_reader(conf) as reader:
        transmission_rpc_url = reader.get_safe('transmission-rpc-url')
        transmission_username = reader.get_safe('transmission-username')
        transmission_passwd = reader.get_safe('transmission-password')
        seedbox_addr = reader.get_safe('seedbox-local-addr')
        seedbox_user = reader.get_safe('seedbox-user')
        ip_check_delay = reader.get_safe('ip-check-delay')
        forbidden_countries = reader.get_safe('forbidden-countries')
        download_speed_delay = reader.get_safe('download-speed-delay')
        pin_loc_ok = reader.get_safe('pin-localization-ok')
        pin_loc_ko = reader.get_safe('pin-localization-ko')
        pin_download = reader.get_safe('pin-download')
        min_freq = reader.get_safe('minimum-frequency')
        max_freq = reader.get_safe('maximum-frequency')
        max_download_speed = reader.get_safe('maximum-download-speed')

    loc_led_mng = BlinkingLocalization(pin_loc_ok, pin_loc_ko, ip_check_delay)
    down_speed_mng = BlinkingDownloadSpeed(pin_download, download_speed_delay,
                                           min_freq, max_freq, max_download_speed)

    localization_checker = partial(check_licit_ip, seedbox_user, seedbox_addr, forbidden_countries)
    transmission_stats_getter = partial(get_transmision_session_stats,
                                        transmission_rpc_url,
                                        transmission_username,
                                        transmission_passwd)

    tasks = [asyncio.create_task(loc_led_mng.check_localisation_status(localization_checker)),
             asyncio.create_task(down_speed_mng.get_download_speed(transmission_stats_getter))]

    if ON_PI:
        tasks.extend([asyncio.create_task(loc_led_mng.blink_led()),
                      asyncio.create_task(down_speed_mng.blink_led())])
        initialize_gpio(pin_loc_ok)
        initialize_gpio(pin_loc_ko)


    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Keyboard interruption!")
    except ClientConnectorError as err:
        print(err)
    finally:
        if ON_PI:
            cleanup()
        sys.exit(0)
