#!/usr/bin/env python3
"""
This program retrieves some informations on a leech box
"""
import json
import requests
from subprocess import check_output, CalledProcessError
import time
from typing import Mapping, Union, Optional, Any, Generator
import sys

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except (ImportError, RuntimeError):
    # For the purpose of testing connection to seedbox we may not be on a raspberry
    ON_PI = False


def get_ip_localisation(seed_box_user:str, seed_box_addr: str) -> Optional[str]:
    """
    Return the public ip country name

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: the public ip country name
    """
    try:
        res_b = check_output(f'ssh {seed_box_user}@{seed_box_addr} curl -s https://ipvigilante.com', shell=True)
    except CalledProcessError:
        return None
    res_s = res_b.decode('utf-8')
    res_d = json.loads(res_s)
    if res_d['status'] != 'success':
        return None
    return res_d['data']['country_name']


def check_licit_ip(seed_box_user:str, seed_box_addr: str) -> bool:
    """
    Return True if the public ip country name is licit

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: True if the public ip country name is licit (false otherwise)
    """
    loc = get_ip_localisation(seed_box_user, seed_box_addr)
    if not loc or loc not in ('Germany', 'Netherlands'):
        return False
    return True


def get_transmission_session_id(url: str) -> Optional[str]:
    """
    Return the transmission session id

    :param url: the transmission rpc url
    """
    response = requests.post(url, auth=('transmission', 'transmission'))
    try:
        return response.headers['X-Transmission-Session-Id']
    except (AttributeError, KeyError):
        return None


def get_transmission_header(url: str) -> Optional[Mapping[str, str]]:
    """
    Return the transmission current session header

    :param url: the transmission rpc url
    """
    session_id = get_transmission_session_id(url)
    if not session_id:
        print("No session id found!", file=sys.stderr)
        return None
    return {'x-transmission-session-id': session_id}


def get_transmision_session_stats(url: str) -> Optional[Mapping[str, Any]]:
    """
    Return the transmission current session stats

    :param url: the transmission rpc url
    """
    s_stats_request = {
        "method": "session-stats",
        "tag": 39693
    }

    header = get_transmission_header(url)

    if not header:
        print("No header found!", file=sys.stderr)
        return None

    response = requests.post(
        url,
        auth=('transmission', 'transmission'),
        headers=get_transmission_header(url),
        json=s_stats_request
    )
    
    if response.status_code != 200:
        print("Response on error!", file=sys.stderr)
        return None

    try:
        return response.json()['arguments']
    except (AttributeError, KeyError):
        print("Unable to get arguments!", file=sys.stderr)
        return None


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


def check_localisation_status(seed_box_user, seed_box_addr: str, delay: int) -> Generator[bool, int, None]:
    """
    Check the localisation status every delay seconds

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :param delay: refreshing delay
    :return: True if the public ip country name is licit (false otherwise)
    """
    start = int(time.time())
    is_licit = check_licit_ip(seed_box_user, seed_box_addr)
    count = 0
    while True:
        current_time = yield is_licit
        c_count = (current_time - start) // delay
        if c_count != count:
            count = c_count
            is_licit = check_licit_ip(seed_box_user, seed_box_addr)


def get_download_speed(transmission_rpc_url: str, delay: int) -> Generator[str, int, None]:
    """
    Yields the download speed every delay seconds
    """
    start = int(time.time())
    stats = get_transmision_session_stats(transmission_rpc_url)
    if not stats:
        return None
    count = 0
    while True:
        current_time = yield stats['downloadSpeed']
        c_count = (current_time - start) // delay
        if c_count != count:
            count = c_count
            stats = get_transmision_session_stats(transmission_rpc_url)
            if not stats:
                return None


def initialize_gpio(led: int) -> None:
    """
    Initalizes the led

    :param led: led index (BOARD mode)
    """
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(True)
    GPIO.setup(led, GPIO.OUT)

    if GPIO.input(led):
        GPIO.output(led, GPIO.LOW)

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

    time_delta = int(min((ip_check_delay, download_speed_delay)) / 2)
    gen_loc_status = check_localisation_status(seedbox_user, seedbox_addr, ip_check_delay)
    next(gen_loc_status)
    gen_speed_ret = get_download_speed(transmission_rpc_url, download_speed_delay)
    next(gen_speed_ret)

    if ON_PI:
        initialize_gpio(pin_loc_ok)
        initialize_gpio(pin_loc_ko)

    while True:
        current_time = int(time.time())
        status = gen_loc_status.send(current_time)
        speed = gen_speed_ret.send(current_time)
        if status:
            print("Status is Ok!")
            if ON_PI:
                GPIO.output(pin_loc_ok, GPIO.HIGH)
                GPIO.output(pin_loc_ko, GPIO.LOW)
        else:
            print("Status is Ko!")
            if ON_PI:
                GPIO.output(pin_loc_ko, GPIO.HIGH)
                GPIO.output(pin_loc_ok, GPIO.LOW)
        if speed:
            print(f"Speed is {speed}")
            if ON_PI:
                GPIO.output(pin_download, GPIO.HIGH)
        else:
            print("No download running!")
            if ON_PI:
                GPIO.output(pin_download, GPIO.LOW)
        time.sleep(time_delta)

    if ON_PI:
        GPIO.cleanup()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("User interruption!", file=sys.stderr)
        sys.exit(0)
    if ON_PI:
        GPIO.cleanup()