# mini-IPMI
## Features
CPU and disk temperature monitoring scripts for zabbix. Also support voltage and fan speed monitoring on certain configurations. Uses lm-sensors, smartmontools and OpenHardwareMonitorReport. For Linux, BSD and Windows.<br />
Although the scripts considers all disks and cores, LLD is not used, and for items not listed in template you have to add it yourself.

#### Advantages
- bulk items upload with zabbix-sender
- no unnecessary processes is spawned
- does not spin idle drives
- no hardcoded devices

#### Disadvantages
- requires configuration
- no Low-Level Discovery
- manual RAID passthrough

![Temperature graph](https://github.com/nobodysu/mini-IPMI/blob/master/screenshots/mini-ipmi_graph-temperature.png?raw=true)

### temp-disk.py
Cross-platform disk temperature monitoring script for zabbix. By default used to display maximum temperature among all disks with `temp.disk[max]`. Can be used to query specific disk with, for example, `temp.disk[0]` - first disk.<br />
It first checks whether disk is in standby mode and only then queries the temperature, thus not spinning drives unnecessary. You can override this behavior by using `temp.disk[max.force]`. It is encouraged, in fact, if your drives are never idle, because this operation not spawns additional process and thus is slightly faster.

### zabbix-lmsensors-wrapper.py
Linux-specific temperature monitoring for CPU, GPU and motherboard sensors. Also supports fan speed and voltage. Expects default lm-sensors output.<br />
The script is always answers to just `temp.cpu[max]`, returning all other keys data with zabbix-sender.

### temp-cpu-bsd.py
CPU temperature monitoring for FreeBSD. Uses `sysctl dev.cpu` with `coretemp` or `amdtemp`.<br />
Only answers to `temp.cpu[max]`, core temperatures are sent with zabbix-sender.

### zabbix-ohmr-wrapper.py
CPU, GPU and motherboard temperature, fan speed and voltage monitoring for Windows.<br />
Always answers to `temp.cpu[max]`, others are sent with zabbix-sender.

## Installation
As prerequisites you need `python34`, `lm-sensors`, `smartmontools`, `sudo` and `zabbix-sender` packages. `python3` meta-package would also be good as scripts answer to `python3` command.<br />
Take a look at scripts first lines and provide paths if needed. If you have a RAID configuration, also provide that by hand. Import `Template_mini-IPMI.xml` in zabbix web interface.

### First step
#### Linux
```bash
mv zabbix-lmsensors-wrapper.py temp-disk.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /etc/sudoers.d/ # place sudoers include here for temp-disk.py sudo access
mv userparameter_mini-ipmi.conf /etc/zabbix/zabbix_agentd.d/ # move zabbix keys include here
```

#### FreeBSD
```bash
mv temp-cpu-bsd.py temp-disk.py /usr/local/etc/zabbix/scripts/
mv sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv userparameter_mini-ipmi.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```
Then, for Intel processor you need to add `coretemp_load="YES"` to `/boot/loader.conf`. For AMD it will be `amdtemp_load="YES"`. Reboot or manual `kldload` is required to take effect.

#### Windows
```cmd
move temp-disk.py C:\zabbix-agent\scripts\
move zabbix-ohmr-wrapper.py C:\zabbix-agent\scripts\
move userparameter_mini-ipmi.conf C:\zabbix-agent\conf\
```

Currently there are two versions of `OpenHardwareMonitorReport`: [0.3.2.0](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/230#issue-102662845) and [0.5.1.7](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/230#issuecomment-133940467). Later gives you wider number of supported sensors, but have disk drives monitoring, which will spin the drives in standby. If you can live with that, choose the latest version.<br />
Install `python3` for all users, adding it to `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in environment variables. `.NET Framework` is also required for `OpenHardwareMonitorReport`. 

### Second step
Then you need to include your zabbix conf folder in `zabbix_agentd.conf`, like this:
```conf
Include=/usr/local/etc/zabbix/zabbix_agentd.conf.d/
```
Also its recomended to add at least `Timeout=5` to config file to allow drives spin up and OHMR execution.

Thats all for Windows. For others run the following to finish configuration:
```bash
chmod 750 scripts/* # apply necessary permissions
chown root:zabbix scripts/*
chmod 640 userparameter_mini-ipmi.conf
chown root:zabbix userparameter_mini-ipmi.conf
chmod 400 sudoers.d/zabbix
chown root sudoers.d/zabbix
visudo # test sudoers configuration
```

## Testing
All scripts except `temp-disk.py` have verbose `-v` switch for debug. Run it and check the output. Example queries:
```bash
./zabbix-lmsensors-wrapper.py -v # execute check and show debug information
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
- remote `-v` debug
- zabbix-sender for `temp-disk.py`, more optimized script
- Low-Level Discovery for all scripts
- voltage and fan monitoring for BSD

## Links
- https://www.smartmontools.org
- https://wiki.archlinux.org/index.php/Lm_sensors
- https://github.com/openhardwaremonitor/openhardwaremonitor
- http://unlicense.org
