#! /usr/bin/python
import re
import subprocess

# example on ps ux result:
# USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# uuuuser+     737  0.0  0.0   2836   992 ?        Ss    2023   0:00 command
# uuuuser+     744  0.0  4.4 2397260 346668 ?      Sl    2023  54:02 command

ps_regexp_fmt = '(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
process_to_print = {}

stats_to_sort = ['pcpu', 'rss']
for stats in stats_to_sort:
  proc = subprocess.Popen(['ps', 'ux', '--sort=pcpu'], stdout=subprocess.PIPE)
  line = proc.stdout.readline() # skip first line
  while True:
    line = proc.stdout.readline()
    if not line:
      break
    re_search_result = re.search(ps_regexp_fmt, str(line))
    if not re_search_result:
      continue;
    user, pid, cpu_percent, mem_percent, vsz, rss, tty, stat, start, time, command = re_search_result.groups()
    process_to_print[pid] = {
      'command': command,
      'cpu_perc': cpu_percent,
      'mem_perc': mem_percent,
      'vsz': vsz,
      'rss': rss,
    }

for pid in process_to_print:
  process_metadata = process_to_print[pid]
  command = process_metadata['command']
  print('cpu_perc{{pid="{pid}",command="{command}"}} {value}'.format(command=command, pid=pid, value=process_metadata['cpu_perc']))
  print('mem_perc{{pid="{pid}",command="{command}"}} {value}'.format(command=command, pid=pid, value=process_metadata['mem_perc']))
  print('vsz_usage{{pid="{pid}",command="{command}"}} {value}'.format(command=command, pid=pid, value=process_metadata['vsz']))
  print('rss_usage{{pid="{pid}",command="{command}"}} {value}'.format(command=command, pid=pid, value=process_metadata['rss']))
  print()

