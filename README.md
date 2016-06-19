# mini-IPMI
## Features
Zabbix scripts for monitoring cpu and disk temperature with aid of lmsensors, smartmontools and OpenHardwareMonitorReport. Supports Linux, BSD and Windows.

## Installation
By prerequisites you need `python34`, `lm-sensors`, `smartmontools`, `sudo` and `zabbix-sender` packages. `python3` meta-package would also be good as scripts answer to `python3` command.<br />
Take a look at scripts first lines and provide paths if needed. If you have a RAID configuration, also provide that by hand. Import `Template_mini-IPMI.xml` in zabbix web interface.

### First step
#### Linux
```bash
mv zabbix-lmsensors-wrapper.py temp-disk.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /etc/sudoers.d/
mv userparameter_mini-ipmi.conf /etc/zabbix/zabbix_agentd.d/
```

#### FreeBSD
```bash
mv temp-cpu-bsd.py temp-disk.py /usr/local/etc/zabbix/scripts/
mv sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv userparameter_mini-ipmi.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```
Then, for Intel processor you need to add `coretemp_load="YES"` to `/boot/loader.conf`. For AMD it will be `amdtemp_load="YES"`. Reboot or manual `kldload` is required to take effect.

#### Windows
There are two versions of `OpenHardwareMonitorReport` currently: [0.3.2.0](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/230#issue-102662845) and [0.5.1.7](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/230#issuecomment-133940467). Later gives you wider number of supported sensors, but have disk drives monitoring, which will spin the drives in standby. Select version according to your needs.<br />
Install `python3` for all users, adding it to `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in environment variables. `.NET Framework` is also required for OHMR. Make sure your .conf file is included in main `zabbix_agentd.conf`. Windows does not require the second step.

### Second step
```bash
chmod 750 scripts/* # apply necessary permissions
chown root:zabbix scripts/*
chmod 640 userparameter_mini-ipmi.conf
chown root:zabbix userparameter_mini-ipmi.conf
chmod 400 sudoers.d/zabbix
chown root sudoers.d/zabbix
visudo # test sudoers configuration
```
Finally, make sure your `userparameter_mini-ipmi.conf` is included in main `zabbix_agentd.conf`.

## Testing
All scripts except `temp-disk.py` have verbose `-v` switch for debug. Run it and check the output. Example queries:
```bash
./zabbix-lmsensors-wrapper.py -v
zabbix_get -s 127.0.0.1 -k temp.disk[max] # maximum disk temperature among all disks
zabbix_get -s 127.0.0.1 -k temp.cpu[max] # maximum processor temperature among all cores
zabbix_get -s 127.0.0.1 -k temp.disk[0] # first disk temperature
zabbix_get -s 127.0.0.1 -k temp.disk[2.force] # check third disk temperature even if its in standby mode
zabbix_get -s 127.0.0.1 -k temp.disk[max.force] # ignore standby mode on any disk
```

These scripts were tested to work with following configurations:
- Centos 6 / Zabbix 2.4 / Python 3.4
- Centos 7 / Zabbix 2.4 / Python 3.4
- FreeBSD 10.1 / Zabbix 2.4 / Python 3.4
- Windows XP / Zabbix 2.4 / Python 3.4
- Windows 7 / Zabbix 2.4 / Python 3.4
- Windows Server 2012 / Zabbix 2.4 / Python 3.4

## Planned features
- zabbix sender for `temp-disk.py`, more optimized script
- low-level discovery for all scripts
- voltage and fan monitoring for BSD

## Links
- https://github.com/openhardwaremonitor/openhardwaremonitor
- https://www.smartmontools.org
- https://wiki.archlinux.org/index.php/Lm_sensors
- http://unlicense.org
