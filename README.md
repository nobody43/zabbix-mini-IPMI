# zabbix-mini-IPMI
CPU and disk temperature monitoring scripts for zabbix. Also support voltage and fan speed monitoring on certain configurations. Uses `lm-sensors`, `smartmontools` and `OpenHardwareMonitorReport`. For Linux, BSD and Windows.

## Features

- Multi-CPU, disk and GPU solution
- Low-Level Discovery
- Bulk item upload with zabbix-sender
- No unnecessary processes are spawned
- Does not spin idle drives
- RAID passthrough (manual)

![Temperature graph](https://github.com/nobodysu/mini-IPMI/blob/master/screenshots/mini-IPMI-graph.png?raw=true)

[More screenshots.](https://github.com/nobodysu/zabbix-mini-IPMI/tree/master/screenshots)

### STANDBY drives
UPD: not relevant anymore. Just use custom 0.8.0.5+.

### Choosing OHMR version
NEW: [Update](https://github.com/openhardwaremonitor/openhardwaremonitor/pull/1115#issuecomment-616230088) your OHMR version!
#### [0.3.2.0](https://github.com/openhardwaremonitor/openhardwaremonitor/issues/230#issue-102662845)
Version for Windows XP.
#### [0.8.0.5](https://github.com/openhardwaremonitor/openhardwaremonitor/pull/1115#issuecomment-462141642)
#### [0.9.2.0](https://github.com/openhardwaremonitor/openhardwaremonitor/pull/1115#issuecomment-616230088)
Only custom param-capable versions are supported on Windows 7+.

## Installation
As prerequisites you need `python3`, `lm-sensors`, `smartmontools`, `sudo` and `zabbix-sender` packages. For testing `zabbix-get` is also required.<br />
Take a look at scripts first lines and provide paths if needed. If you have custom RAID configuration, also provide that by hand. Import `Template_mini-IPMI_v2.xml` in zabbix web interface.
### Debian / Ubuntu
```sh
client# apt install python3 sudo zabbix-agent zabbix-sender smartmontools lm-sensors
server# apt install zabbix-get
```
### Centos
```sh
client# yum install python3 sudo zabbix-agent zabbix-sender smartmontools lm_sensors
server# yum install zabbix-get
```
### First step
#### Linux
```bash
mv mini_ipmi_smartctl.py Linux/mini_ipmi_lmsensors.py sender_wrapper.py /etc/zabbix/scripts/
mv Linux/sudoers.d/zabbix /etc/sudoers.d/   # place sudoers include here for mini_ipmi_smartctl.py sudo access
mv Linux/zabbix_agentd.d/userparameter_mini-ipmi2.conf /etc/zabbix/zabbix_agentd.d/
```

#### FreeBSD
```bash
mv mini_ipmi_smartctl.py BSD/mini_ipmi_bsdcpu.py sender_wrapper.py /etc/zabbix/scripts/
mv BSD/sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv BSD/zabbix_agentd.conf.d/userparameter_mini-ipmi2.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```
Then, for Intel processor you need to add `coretemp_load="YES"` to `/boot/loader.conf`. For AMD it will be `amdtemp_load="YES"`. Reboot or manual `kldload` is required to take effect.

#### Windows
```cmd
move mini_ipmi_smartctl.py C:\zabbix-agent\scripts\
move mini_ipmi_ohmr.py C:\zabbix-agent\scripts\
move sender_wrapper.py C:\zabbix-agent\scripts\
move userparameter_mini-ipmi2.conf C:\zabbix-agent\zabbix_agentd.conf.d\
```
Install `python3` for [all users](https://github.com/nobodysu/zabbix-mini-IPMI/blob/master/screenshots/mini-IPMI-python-installation1.png), [adding it to](https://github.com/nobodysu/zabbix-mini-IPMI/blob/master/screenshots/mini-IPMI-python-installation2.png) `PATH` during installation. Install `smartmontools` and add its bin folder to `PATH` in environment variables. `.NET Framework` is also required for `OpenHardwareMonitorReport`.

### Second step
Then you need to include your zabbix conf folder in `zabbix_agentd.conf`, like this:
```conf
Include=/usr/local/etc/zabbix/zabbix_agentd.conf.d/
```
Also its recomended to add at least `Timeout=10` to config file to allow drives spun up and OHMR execution.

Thats all for Windows. For others run the following to finish configuration:
```bash
chmod 755 scripts/mini_ipmi*.py scripts/sender_wrapper.py   # apply necessary permissions
chown root:zabbix scripts/mini_ipmi*.py scripts/sender_wrapper.py 
chmod 644 userparameter_mini-ipmi2.conf
chown root:zabbix userparameter_mini-ipmi2.conf
chmod 400 sudoers.d/zabbix
chown root sudoers.d/zabbix
visudo   # test sudoers configuration, type :q! to exit
```

## Testing
```bash
zabbix_get -s 192.0.2.1 -k mini.cputemp.discovery[get,"Example host"]
zabbix_get -s 192.0.2.1 -k mini.disktemp.discovery[get,"Example host"]
```
Default operation mode. Displays json that server should get, detaches, then waits and sends data with zabbix-sender. `Example host` is your `Host name` field in zabbix.
<br /><br />

```bash
zabbix_get -s 192.0.2.1 -k mini.cputemp.discovery[getverb,"Example host"]
zabbix_get -s 192.0.2.1 -k mini.disktemp.discovery[getverb,"Example host"]
```
Verbose mode. Does not detaches or prints LLD. Lists all items sent to zabbix-sender, also it is possible to see sender output in this mode.
<br /><br />

These scripts were tested to work with following configurations:
- Centos 7 / Zabbix 3.0 / Python 3.6
- Debian 9 / Zabbix 3.0 / Python 3.5
- Debian 10 / Server 5.0 / Agent 4.0 / Python 3.7
- Ubuntu 17.10 / Zabbix 3.0 / Python 3.6
- FreeBSD 10.3 / Zabbix 3.0 / Python 3.6
- Windows XP / Zabbix 3.0 / Python 3.4
- Windows 7 / Zabbix (3.0, 5.0) / Python (3.4, 3.7, 3.8)
- Windows Server 2012 / Zabbix 3.0 / Python 3.7

## Known issues
- Zabbix web panel displays an error on json discovery, but everything works fine ([#18](https://github.com/nobodysu/zabbix-mini-IPMI/issues/18))
- Windows version does not detaches, and data will only be gathered on second pass (probably permanent workaround)

## Links
- https://www.smartmontools.org
- https://wiki.archlinux.org/index.php/Lm_sensors
- https://github.com/openhardwaremonitor/openhardwaremonitor
- https://unlicense.org
- [Disk SMART monitoring solution](https://github.com/nobodysu/zabbix-smartmontools)
- [Last Zabbix 2.4 version](https://github.com/nobodysu/zabbix-mini-IPMI/tree/last_zabbix24_unsupported)
- [Older unsupported mini-IPMI version with simpler approach](https://github.com/nobodysu/zabbix-mini-IPMI/tree/old_v1_unsupported)
