| Key                                                          | Supported in        |
| ------------------------------------------------------------ | ------------------- |
| mini.brd.info[BIOSvendor]                                    | mini_ipmi_ohmr.py   |
| mini.brd.info[BIOSversion] | mini_ipmi_ohmr.py   |
|mini.brd.info[MainboardManufacturer]|mini_ipmi_ohmr.py|
|mini.brd.info[MainboardName]|mini_ipmi_ohmr.py|
|mini.brd.info[MainboardVersion]|mini_ipmi_ohmr.py|
|mini.brd.info[SMBIOSversion]|mini_ipmi_ohmr.py|
|mini.brd.info[vcoreMax]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.info[vttMax]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.temp[MAX]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[_N_]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.cpu.info[ConfigStatus]| mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py, mini_ipmi_bsdcpu.py|
|mini.cpu.temp[MAX]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py, mini_ipmi_bsdcpu.py|
|mini.gpu.temp[MAX]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.info[OHMRver]| mini_ipmi_ohmr.py|
|mini.brd.fan[{#BRDFANNUM},rpm]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.temp[{#BRDTEMPNUM}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#P5V}]|mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#P12V}]|mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#P33V}]|mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#VAVCC}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#VBAT}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py| |
|mini.brd.vlt[{#VCC3V}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#VCORE}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#VSB3V}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.brd.vlt[{#VTT}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.cpu.info[cpu{#CPU},CPUstatus]|mini_ipmi_ohmr.py|
|mini.cpu.info[cpu{#CPU},ID]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|	mini.cpu.info[cpu{#CPU},TjMax]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.cpu.temp[cpu{#CPUC},core{#CORE}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py, mini_ipmi_bsdcpu.py|
|mini.cpu.temp[cpu{#CPU},MAX]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py, mini_ipmi_bsdcpu.py|
|	mini.gpu.fan[gpu{#GPUFAN},rpm]|mini_ipmi_ohmr.py|
|mini.gpu.info[gpu{#GPU},GPUstatus]|mini_ipmi_ohmr.py|
|mini.gpu.info[gpu{#GPU},ID]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.gpu.memory[gpu{#GPUMEM},free]|mini_ipmi_ohmr.py|
|mini.gpu.memory[gpu{#GPUMEM},total]|mini_ipmi_ohmr.py|
|mini.gpu.memory[gpu{#GPUMEM},used]|mini_ipmi_ohmr.py|
|mini.gpu.temp[gpu{#GPUTEMP}]|mini_ipmi_ohmr.py, mini_ipmi_lmsensors.py|
|mini.disk.info[ConfigStatus]|mini_ipmi_smartctl.py|
|mini.disk.info[{#DISK},DriveStatus]|mini_ipmi_smartctl.py|
|mini.disk.temp[{#DISK}]|mini_ipmi_smartctl.py|
|mini.disk.temp[MAX]|mini_ipmi_smartctl.py|
