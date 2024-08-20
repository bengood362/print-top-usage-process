#! /usr/bin/python
import re
import subprocess

# example on ps ux result:
# USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# uuuuser+     737  0.0  0.0   2836   992 ?        Ss    2023   0:00 command
# uuuuser+     744  0.0  4.4 2397260 346668 ?      Sl    2023  54:02 command
top_process_count = 4
ps_regexp_fmt = '(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)'
command_prefix_to_replace = 'cmd_'
pid_prefix_to_replace = 'pid_'
process_to_print = {}

def sanitize_label_value(string, prefix_to_replace):
  # label_value must match [a-zA-Z_][a-zA-Z0-9_]*
  # https://prometheus.io/docs/concepts/data_model/
  (first_char, *rest_chars) = string
  if not re.match('[a-zA-Z_]', first_char):
    rest_chars = [first_char, *rest_chars]
    first_char = prefix_to_replace
  rest_chars = list(map(lambda c: c if re.match('[a-zA-Z0-9_]', c) else '_', rest_chars))
  return ''.join([first_char, *rest_chars])

stats_to_sort = ['-pcpu', '-rss']
for stats in stats_to_sort:
  proc = subprocess.Popen(['ps', 'ux', '--sort={}'.format(stats)], stdout=subprocess.PIPE)
  line = proc.stdout.readline() # skip first line
  count = 0
  while True:
    line = proc.stdout.readline().decode('ascii')
    if not line or count > top_process_count:
      break
    re_search_result = re.search(ps_regexp_fmt, line)
    if not re_search_result:
      continue;
    user, pid, cpu_percent, mem_percent, vsz, rss, tty, stat, start, time, command = re_search_result.groups()
    process_to_print[pid] = {
      'command': command.strip().split(' ')[0],
      'cpu_perc': cpu_percent.strip(),
      'mem_perc': mem_percent.strip(),
      'vsz': vsz.strip(),
      'rss': rss.strip(),
    }
    count += 1

for pid in process_to_print:
  process_metadata = process_to_print[pid]
  command = process_metadata['command']
  cpu_perc = process_metadata['cpu_perc']
  mem_perc = process_metadata['mem_perc']
  vsz = process_metadata['vsz']
  rss = process_metadata['rss']

  if cpu_perc > 0:
    print('cpu_perc{{pid="{pid}", command="{command}"}} {value}'.format(
      command=sanitize_label_value(command, command_prefix_to_replace),
      pid=sanitize_label_value(pid, pid_prefix_to_replace),
      value=cpu_perc,
    ))
  if mem_perc > 0:
    print('mem_perc{{pid="{pid}", command="{command}"}} {value}'.format(
      command=sanitize_label_value(command, command_prefix_to_replace),
      pid=sanitize_label_value(pid, pid_prefix_to_replace),
      value=mem_perc,
    ))
  if vsz > 0:
    print('vsz_usage{{pid="{pid}", command="{command}"}} {value}'.format(
      command=sanitize_label_value(command, command_prefix_to_replace),
      pid=sanitize_label_value(pid, pid_prefix_to_replace),
      value=vsz,
    ))
  if rss > 0:
    print('rss_usage{{pid="{pid}", command="{command}"}} {value}'.format(
      command=sanitize_label_value(command, command_prefix_to_replace),
      pid=sanitize_label_value(pid, pid_prefix_to_replace),
      value=rss,
    ))
  print()

