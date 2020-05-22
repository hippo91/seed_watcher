#!/usr/bin/env python3
"""
This program retrieves some informations on a seed box
"""
import asyncio
from contextlib import contextmanager
import json
import os
import signal
import sys
from typing import Mapping, Union, Optional, Generator

from src.localization import BlinkingLocalization
from src.transmission import BlinkingDownloadSpeed
from src.raspberry import ON_PI, initialize_gpio, cleanup


ConfigurationMapping = Mapping[str, Union[int, float]]


def do_sigterm():
    """SIGTERM triggers the KeyboardInterrupt handler."""
    raise KeyboardInterrupt


def read_config() -> Optional[ConfigurationMapping]:
    """
    Read the configuration file and return a dict
    """
    try:
        with open("config.json", 'r') as conf_file:
            data = json.load(conf_file)
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

    def get_safe(self, parameter: str) -> Optional[Union[int, float]]:
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


def main():
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
        seedbox_addr = reader.get_safe('seedbox-local-addr')
        seedbox_user = reader.get_safe('seedbox-user')
        ip_check_delay = reader.get_safe('ip-check-delay')
        download_speed_delay = reader.get_safe('download-speed-delay')
        pin_loc_ok = reader.get_safe('pin-localization-ok')
        pin_loc_ko = reader.get_safe('pin-localization-ko')
        pin_download = reader.get_safe('pin-download')

    loop = asyncio.get_event_loop()
    loc_led_mng = BlinkingLocalization(pin_loc_ok, pin_loc_ko, seedbox_user,
                                       seedbox_addr, ip_check_delay)
    down_speed_mng = BlinkingDownloadSpeed(pin_download, transmission_rpc_url, download_speed_delay)

    tasks = [loop.create_task(loc_led_mng.check_localisation_status()),
             loop.create_task(loc_led_mng.blink_led()),
             loop.create_task(down_speed_mng.get_download_speed()),
             loop.create_task(down_speed_mng.blink_led())]

    if ON_PI:
        initialize_gpio(pin_loc_ok)
        initialize_gpio(pin_loc_ko)

    loop.add_signal_handler(signal.SIGTERM, do_sigterm)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        aggregate = asyncio.gather(tasks)
        aggregate.cancel()
        loop.run_until_complete(aggregate)

    loop.close()

    if ON_PI:
        cleanup()


if __name__ == "__main__":
    main()
