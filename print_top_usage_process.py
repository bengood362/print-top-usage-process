#! /usr/bin/python
import argparse
import re
import subprocess
import getpass

# Argparse
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--pid', metavar='PID', default=[], type=int, nargs='*', help='pid to monitor')
args = parser.parse_args()
pids_to_fetch = list(map(str, args.pid))

# Configs:
top_process_count = 4
ps_regexp_fmt = '(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)'
top_regexp_fmt = '(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
command_prefix_to_replace = 'cmd_'
pid_prefix_to_replace = 'pid_'

current_user = getpass.getuser()

# NOTE: no longer being used, use top now: https://superuser.com/a/1389942/1356854
# example on ps ux result:
# USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# uuuuser+     737  0.0  0.0   2836   992 ?        Ss    2023   0:00 command
# uuuuser+     744  0.0  4.4 2397260 346668 ?      Sl    2023  54:02 command

def sanitize_label_value(string, prefix_to_replace):
  # label_value must match [a-zA-Z_][a-zA-Z0-9_]*
  # https://prometheus.io/docs/concepts/data_model/
  (first_char, *rest_chars) = string
  if not re.match('[a-zA-Z_]', first_char):
    rest_chars = [first_char, *rest_chars]
    first_char = prefix_to_replace
  rest_chars = list(map(lambda c: c if re.match('[a-zA-Z0-9_]', c) else '_', rest_chars))
  return ''.join([first_char, *rest_chars])

def parse_vsz(value):
  if 'g' in value:
    return str(float(value[:-1]) * (1024**3))
  return value

def parse_top_process_stats(line):
  if not line:
    return None
  re_search_result = re.search(top_regexp_fmt, line)
  if not re_search_result:
    return None
  pid, user, pr, ni, virt, res, shr, s, cpu_perc, mem_perc, cpu_time, cmd = re_search_result.groups()
  return pid, {
    'command': cmd.strip(),
    'cpu_perc': cpu_perc.strip(),
    'mem_perc': mem_perc.strip(),
    'rss': parse_vsz(res).strip(),
    'vsz': parse_vsz(virt).strip(),
  }

def parse_ps_process_stats(line):
  if not line:
    return None
  re_search_result = re.search(ps_regexp_fmt, line)
  if not re_search_result:
    return None
  user, pid, cpu_perc, mem_perc, vsz, rss, tty, stat, start, time, cmd = re_search_result.groups()
  return pid, {
      'command': cmd.strip().split(' ')[0],
      'cpu_perc': cpu_perc.strip(),
      'mem_perc': mem_perc.strip(),
      'vsz': vsz.strip(),
      'rss': rss.strip(),
    }

def process_processes_result_by_ps():
  processes_result = {}
  ps_stats_to_sort = ['-pcpu', '-rss']
  for stats in ps_stats_to_sort:
    proc = subprocess.Popen(['ps', 'ux', '--sort={}'.format(stats)], stdout=subprocess.PIPE)
    line = proc.stdout.readline() # skip first line
    count = 0
    while line:
      line = proc.stdout.readline().decode('ascii')
      process_stat_result = parse_ps_process_stats(line)
      if process_stat_result:
        pid, processes_result[pid] = process_stat_result
      if (pid not in pids_to_fetch):
        count += 1
      if count > top_process_count:
        break;

  if len(pids_to_fetch) > 0:
    proc = subprocess.Popen(['ps', 'ux', *pids_to_fetch], stdout=subprocess.PIPE)
    for _ in range(7):
      # skip first 7 lines
      line = proc.stdout.readline().decode('ascii')
    while line:
      line = proc.stdout.readline().decode('ascii')
      process_stat_result = parse_ps_process_stats(line)
      if process_stat_result:
        pid, processes_result[pid] = process_stat_result

  return processes_result;

def process_processes_result_by_top():
  processes_result = {}
  top_stats_to_sort = ['+%CPU', '+RES']
  for stats in top_stats_to_sort:
    proc = subprocess.Popen(['top', '-bn1', '-u', current_user, '-o', stats], stdout=subprocess.PIPE)
    for _ in range(7):
      # skip first 7 lines
      line = proc.stdout.readline().decode('ascii')
    count = 0
    while line:
      line = proc.stdout.readline().decode('ascii')
      process_stat_result = parse_top_process_stats(line)
      if process_stat_result:
        pid, processes_result[pid] = process_stat_result
      if (pid not in pids_to_fetch):
        count += 1
      if count > top_process_count:
        break;

  if len(pids_to_fetch) > 0:
    proc = subprocess.Popen(['top', '-bn1', '-p', ','.join(pids_to_fetch)], stdout=subprocess.PIPE)
    for _ in range(7):
      next(proc.stdout)
    while line:
      line = proc.stdout.readline().decode('ascii')
      process_stat_result = parse_top_process_stats(line)
      if process_stat_result:
        pid, processes_result[pid] = process_stat_result

  return processes_result;

processes_result = process_processes_result_by_top();

for pid in processes_result:
  process_metadata = processes_result[pid]
  command = process_metadata['command']
  cpu_perc = process_metadata['cpu_perc']
  mem_perc = process_metadata['mem_perc']
  vsz = process_metadata['vsz']
  rss = process_metadata['rss']
  isTarget = pid in pids_to_fetch

  print('cpu_perc{{pid="{pid}", command="{command}", isTarget="{isTarget}"}} {value}'.format(
    command=sanitize_label_value(command, command_prefix_to_replace),
    pid=sanitize_label_value(pid, pid_prefix_to_replace),
    isTarget=isTarget,
    value=cpu_perc,
  ))
  print('mem_perc{{pid="{pid}", command="{command}", isTarget="{isTarget}"}} {value}'.format(
    command=sanitize_label_value(command, command_prefix_to_replace),
    pid=sanitize_label_value(pid, pid_prefix_to_replace),
    isTarget=isTarget,
    value=mem_perc,
  ))
  print('vsz_usage{{pid="{pid}", command="{command}", isTarget="{isTarget}"}} {value}'.format(
    command=sanitize_label_value(command, command_prefix_to_replace),
    pid=sanitize_label_value(pid, pid_prefix_to_replace),
    isTarget=isTarget,
    value=vsz,
  ))
  print('rss_usage{{pid="{pid}", command="{command}", isTarget="{isTarget}"}} {value}'.format(
    command=sanitize_label_value(command, command_prefix_to_replace),
    pid=sanitize_label_value(pid, pid_prefix_to_replace),
    isTarget=isTarget,
    value=rss,
  ))
  print()
