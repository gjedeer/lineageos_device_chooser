#!/usr/bin/python

import glob
import os
import os.path
import requests
import yaml
from bs4 import BeautifulSoup

def get_stats_soup():
    if not os.path.exists('stats.html'):
        r = requests.get('https://stats.lineageos.org')
        with open('stats.html', 'w') as f:
            f.write(r.text.encode('utf8'))
        text = r.text
    else:
        print "(reading cached stats.html)"
        text = open('stats.html').read()
    soup = BeautifulSoup(text, 'html.parser')
    return soup

def get_stats():
    rv = {}
    root = get_stats_soup()
    devices = root.find(id='top-devices')
    stats = devices.find_all(class_='leaderboard-row')
    for position, stat in enumerate(stats):
        name = stat.find(class_='leaderboard-left').find('a').text.strip()
        num_users_str = stat.find(class_='leaderboard-right').text
        num_users = int(num_users_str)
        rv[name] = {
            'users': num_users,
            'position': position,
            'popularity': position,
        }

    return rv

def get_devices():
    rv = {}
    for filename in glob.iglob('lineage_wiki/_data/devices/*.yml'):
        data = yaml.load(open(filename))
        ram_clean = ' '.join(data['ram'].split(' ')[:2])
        ram_clean = ram_clean.split('/')[-1]
	ram_b = human2bytes(ram_clean)
        data['ram_mb'] = ram_b/(1024*1024)
        rv[data['codename']] = data

    return rv

def annotate_devices_with_stats(devices, stats):
    for device_name, obj in devices.iteritems():       
        if device_name in stats:
            devices[device_name].update(stats[device_name])

def human2bytes(s):
    """
    Attempts to guess the string format based on default symbols
    set and return the corresponding bytes as an integer.
    When unable to recognize the format ValueError is raised.

      >>> human2bytes('0 B')
      0
      >>> human2bytes('1 K')
      1024
      >>> human2bytes('1 M')
      1048576
      >>> human2bytes('1 Gi')
      1073741824
      >>> human2bytes('1 tera')
      1099511627776

      >>> human2bytes('0.5kilo')
      512
      >>> human2bytes('0.1  byte')
      0
      >>> human2bytes('1 k')  # k is an alias for K
      1024
      >>> human2bytes('12 foo')
      Traceback (most recent call last):
          ...
      ValueError: can't interpret '12 foo'
    """
    SYMBOLS = {
	'customary'     : ('B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'),
	'customary_comp'     : ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'),
	'customary_ext' : ('byte', 'kilo', 'mega', 'giga', 'tera', 'peta', 'exa',
			'zetta', 'iotta'),
	'iec'           : ('Bi', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi'),
	'iec_ext'       : ('byte', 'kibi', 'mebi', 'gibi', 'tebi', 'pebi', 'exbi',
			'zebi', 'yobi'),
    }
    init = s
    num = ""
    while s and s[0:1].isdigit() or s[0:1] == '.':
        num += s[0]
        s = s[1:]
    num = float(num)
    letter = s.strip()
    for name, sset in SYMBOLS.items():
        if letter in sset:
            break
    else:
        if letter == 'k':
            # treat 'k' as an alias for 'K' as per: http://goo.gl/kTQMs
            sset = SYMBOLS['customary']
            letter = letter.upper()
        else:
            raise ValueError("can't interpret %r" % init)
    prefix = {sset[0]:1}
    for i, s in enumerate(sset[1:]):
        prefix[s] = 1 << (i+1)*10
    return int(num * prefix[letter])

def battery_removable(device):
    if device['battery'] == 'None':
        return False
    try:
        if not device['battery']['removable']:
            return False
    except TypeError:
        bad = 1
        for subdev in device['battery']:
            for k, v in subdev.iteritems():
                if v.get('removable', 0):
                    bad = 0
        if bad:
            return False

    return True

if __name__ == "__main__":
    stats = get_stats()
    devices = get_devices()
    annotate_devices_with_stats(devices, stats)

    candidates = []

    for name, device in devices.iteritems():
        if 'sdcard' not in device: 
            continue
        if device['current_branch'] < 14:
            continue
        if device['ram_mb'] < 2048:
            continue
        if not battery_removable(device):
            continue
        if len(device['maintainers']) == 0:
            continue

        candidates.append(device)

    candidates.sort(key=lambda x:x['popularity'])
    for device in candidates:
        print device['codename'], '\t', device['vendor'], device['name']
