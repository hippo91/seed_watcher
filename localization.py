"""
This module holds functions that deal with ip localization of the seed box
"""
import asyncio
import json
import time
from typing import Optional, AsyncGenerator

from raspberry import blink_led


async def get_ip_localisation(seed_box_user:str, seed_box_addr: str) -> Optional[str]:
    """
    Return the public ip country name

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: the public ip country name
    """
    cmd = f'ssh {seed_box_user}@{seed_box_addr} curl -s https://ipvigilante.com'
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if stdout:
        res_s = stdout.decode()
        res_d = json.loads(stdout)
        if res_d['status'] != 'success':
            return None
        return res_d['data']['country_name']

    print("Unable to get ip localization", file=sys.stderr)
    print(f"Error is {stderr.decode()}", file=sys.stderr)
    return None


async def check_licit_ip(seed_box_user:str, seed_box_addr: str) -> bool:
    """
    Return True if the public ip country name is licit

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :return: True if the public ip country name is licit (false otherwise)
    """
    loc = await get_ip_localisation(seed_box_user, seed_box_addr)
    if not loc or loc not in ('Germany', 'Netherlands'):
        return False
    return True


async def check_localisation_status(seed_box_user, seed_box_addr: str, delay: int, pin_ok: int, pin_ko: int) -> bool:
    """
    Check the localisation status every delay seconds

    :param seed_box_user: user name on the seed box
    :param seed_box_addr: address of the seed box on the internal network
    :param delay: refreshing delay
    :return: True if the public ip country name is licit (false otherwise)
    """
    while True:
        is_licit = await check_licit_ip(seed_box_user, seed_box_addr)
        if is_licit:
            await blink_led(pin_ok)
        else:
            await blink_led(pin_ko)
        print(f"Ip address is licit : {is_licit}")
        await asyncio.sleep(delay)