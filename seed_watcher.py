#!/usr/bin/env python3
"""
This program retrieves some informations on a leech box
"""
import asyncio
import json
import signal
import sys
import time
from typing import Mapping, Union, Optional

from localization import BlinkingLocalization
from transmission import BlinkingDownloadSpeed
from raspberry import ON_PI, initialize_gpio, cleanup


def do_sigterm():
    """SIGTERM triggers the KeyboardInterrupt handler."""
    raise KeyboardInterrupt


def read_config() -> Optional[Mapping[str, Union[int, float]]]:
    """
    Read the configuration file and return a dict
    """
    try:
        with open("config.json", 'r') as fi:
            data = json.load(fi)
    except FileNotFoundError:
        return None
    return data


def main():
    conf = read_config()
    if not conf:
        print("Error! The configuration file (config.json) has not been found!", file=sys.stderr)
        sys.exit(1)
    
    try:
        transmission_rpc_url = conf['transmission-rpc-url']
        seedbox_addr = conf['seedbox-local-addr']
        seedbox_user = conf['seedbox-user']
        ip_check_delay = conf['ip-check-delay']
        download_speed_delay = conf['download-speed-delay']
        pin_loc_ok = conf['pin-localization-ok']
        pin_loc_ko = conf['pin-localization-ko']
        pin_download = conf['pin-download']
    except KeyError:
        print("Error! The configuration file is not well formed!", file=sys.stderr)
        if 'transmission-rpc-url' not in conf.keys():
            print("\tThe parameter 'transmission-rpc-url' has not been found!", file=sys.stderr)
        if 'seedbox-local-addr' not in conf.keys():
            print("\tThe parameter 'seedbox-local-addr' has not been found!", file=sys.stderr)
        if 'seedbox-user' not in conf.keys():
            print("\tThe parameter 'seedbox-user' has not been found!", file=sys.stderr)
        if 'ip-check-delay' not in conf.keys():
            print("\tThe parameter 'ip-check-delay' has not been found!", file=sys.stderr)
        if 'download-speed-delay' not in conf.keys():
            print("\tThe parameter 'download-speed-delay' has not been found!", file=sys.stderr)
        if 'pin-localization-ok' not in conf.keys():
            print("\tThe parameter 'pin-localization-ok' has not been found!", file=sys.stderr)
        if 'pin-localization-ko' not in conf.keys():
            print("\tThe parameter 'pin-localization-ko' has not been found!", file=sys.stderr)
        if 'pin-download' not in conf.keys():
            print("\tThe parameter 'pin-download' has not been found!", file=sys.stderr)
        sys.exit(2)


    loop = asyncio.get_event_loop()
    loc_led_mng = BlinkingLocalization(conf['pin-localization-ok'], conf['pin-localization-ko']) 
    loc_status_task = loop.create_task(loc_led_mng.check_localisation_status(seedbox_user, seedbox_addr, ip_check_delay))
    loc_led_task = loop.create_task(loc_led_mng.blink_led())
    down_speed_mng = BlinkingDownloadSpeed(conf['pin-download'])
    down_speed_task = loop.create_task(down_speed_mng.get_download_speed(transmission_rpc_url, download_speed_delay))
    down_speed_led_task = loop.create_task(down_speed_mng.blink_led())

    if ON_PI:
        initialize_gpio(pin_loc_ok)
        initialize_gpio(pin_loc_ko)

    loop.add_signal_handler(signal.SIGTERM, do_sigterm)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        aggregate = asyncio.gather(loc_status_task, down_speed_task, loc_led_task)
        aggregate.cancel()
        loop.run_until_complete(aggregate)

    loop.close()


    if ON_PI:
        cleanup()


if __name__ == "__main__":
    main()