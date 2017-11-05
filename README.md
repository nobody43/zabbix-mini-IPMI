# zabbix-mini-IPMI
## Features

- Low-Level Discovery
- Bulk items upload with zabbix-sender
- No unnecessary processes are spawned
- Does not spin idle drives
- RAID passthrough (manual)

### Choosing OHMR version
### STANDBY drives

## Installation
### First step
#### Linux
```bash
mv mini_ipmi_smartctl.py mini_ipmi_lmsensors.py sender_wrapper.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /etc/sudoers.d/ # place sudoers include here for mini_ipmi_smartctl.py sudo access
mv userparameter_mini-ipmi2.conf /etc/zabbix/zabbix_agentd.d/
```

#### FreeBSD
```bash
mv mini_ipmi_smartctl.py mini_ipmi_bsdcpu.py sender_wrapper.py /etc/zabbix/scripts/
mv sudoers.d/zabbix /usr/local/etc/sudoers.d/
mv userparameter_mini-ipmi2.conf /usr/local/etc/zabbix/zabbix_agentd.d/
```

#### Windows
```cmd
move mini_ipmi_smartctl.py C:\zabbix-agent\scripts\
move mini_ipmi_ohmr.py C:\zabbix-agent\scripts\
move sender_wrapper.py C:\zabbix-agent\scripts\
move userparameter_mini-ipmi2.conf C:\zabbix-agent\conf\
```

### Second step

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
- Centos 7 / Zabbix 2.4 / Python 3.4
- Debian 8 / ZS (2.4, 3.4) / ZA (2.4, 3.4) / Python 3.4
- FreeBSD 10.3 / Zabbix 2.4 / Python 3.6
- Windows XP / Zabbix 2.4 / Python 3.4
- Windows 7 / ZS (2.4, 3.4) / ZA (2.4, 3.4) / Python 3.4
- Windows Server 2012 / Zabbix 2.4 / Python 3.4

## Links
- https://www.smartmontools.org
- https://wiki.archlinux.org/index.php/Lm_sensors
- https://github.com/openhardwaremonitor/openhardwaremonitor
- https://unlicense.org
- [Disk SMART monitoring solution](https://github.com/nobodysu/zabbix-smartmontools)
