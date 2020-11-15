import argparse
import copy
import datetime
import glob
import json
import os
import subprocess
import sys
import time
import webbrowser

args = None
collector_path = None
monitor_path = None
task = None
evidence_output_path = None
report_output_path = None
delay = 10
result = []

def start_vm():
    print('[*] Starting VM')
    # jump to the snapshot
    cmd = ['vmrun', 'revertToSnapshot', task['vm'], task['snapshot']]
    subprocess.run(cmd)
    # magic delay before starting
    time.sleep(1)
    # start vm
    cmd = ['vmrun', 'start', task['vm']]
    subprocess.run(cmd)

def copy_task_files():
    print('[*] Copying task files (Host -> Guest)')
    # copy file from host to guest according to the task file
    for f in task['files']:
        cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'copyFileFromHostToGuest', task['vm'], f['source'], f['target']]
        subprocess.run(cmd)

def run_task():
    # wait for the monitors to start properly
    time.sleep(delay)
    print(f'[*] Running task for {task["time"]} seconds')
    # run commands according to the task file
    for c in task['commands']:
        if c['permission'] == 'root':
            user = 'root'
            password = task['root_password']
        elif c['permission'] == 'user':
            user = task['user_name']
            password = task['user_password']
        cmd = ['vmrun', '-gu', user, '-gp', password, 'runProgramInGuest', task['vm'], '-noWait'] + c['command'].split(' ')
        subprocess.run(cmd)

def collector():
    print('[*] Running collector')
    # run macoscollector
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'runProgramInGuest', task['vm'],
            '/bin/bash', '-c', f'cd {collector_path} && python3 run.py -c']
    subprocess.run(cmd)

def copy_artifacts():
    print('[*] Copying artifacts (Guest -> Host)')
    # create archive
    archive_path = f'{collector_path}/artifacts.tar.gz'
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'runProgramInGuest', task['vm'],
            '/usr/bin/tar', '-czf', archive_path, '-C', collector_path, './artifacts']
    subprocess.run(cmd)
    # copy archive to host
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'copyFileFromGuestToHost', task['vm'], archive_path, evidence_output_path]
    subprocess.run(cmd)
    # extract archive
    cmd = ['tar', '-xzf', f'{evidence_output_path}artifacts.tar.gz', '-C', evidence_output_path]
    subprocess.run(cmd)
    cmd = ['rm', f'{evidence_output_path}artifacts.tar.gz']
    subprocess.run(cmd)
    print(f'    [+] Save to \'{evidence_output_path}artifacts/\'')

def monitor():
    print('[*] Running monitor')
    # add monitoring time with delay time
    time = str(int(task['time']) + delay)
    # run macosmonitor
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'runProgramInGuest', task['vm'], '-noWait',
            '/bin/bash', '-c', f'cd {monitor_path} && python3 run.py -m -t {time}']
    subprocess.run(cmd)

def copy_logs():
    print('[*] Copying logs (Guest -> Host)')
    # create archive
    archive_path = f'{monitor_path}/logs.tar.gz'
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'runProgramInGuest', task['vm'],
            '/usr/bin/tar', '-czf', archive_path, '-C', monitor_path, './logs']
    subprocess.run(cmd)
    # copy archive
    cmd = ['vmrun', '-gu', 'root', '-gp', task['root_password'], 'copyFileFromGuestToHost', task['vm'], archive_path, evidence_output_path]
    subprocess.run(cmd)
    # extract archive
    cmd = ['tar', '-xzf', f'{evidence_output_path}logs.tar.gz', '-C', evidence_output_path]
    subprocess.run(cmd)
    cmd = ['rm', f'{evidence_output_path}logs.tar.gz']
    subprocess.run(cmd)
    print(f'    [+] Save to \'{evidence_output_path}logs/\'')

def suspend_vm():
    print('[*] Suspending VM')
    # suspend vm
    cmd = ['vmrun', 'suspend', task['vm']]
    subprocess.run(cmd)

def copy_memory():
    print('[*] Copying memory (Guest -> Host)')
    # get memory file path
    vmem = glob.glob(f'{task["vm"][:-4]}-????????.vmem')
    # copy memory
    cmd = ['cp', vmem[0], evidence_output_path]
    subprocess.run(cmd)

def resume_vm():
    print('[*] Resuming VM')
    # start vm
    cmd = ['vmrun', 'start', task['vm']]
    subprocess.run(cmd)

def report(tactic, t, s_name, p, s, evidence, tool):
    # create report block
    block = {}
    block['tactic'] = tactic
    block['id'] = t['id']
    block['name'] = t['name']
    block['source'] = s_name
    block['pattern'] = p
    block['data'] = s
    block['evidence'] = evidence
    block['tool'] = tool
    return block

def match(source, pattern, tactic, t, s_name, evidence, tool):
    # match source with pattern
    for s in source:
        detected = False
        for p in pattern:
            if detected:
                break
            # for 'and' condition
            if 'and' in p:
                satisfied = True
                for a in p['and']:
                    if not satisfied:
                        break
                    item = s.get(a['key'], '(null)')
                    # compare str with list
                    if type(item) is str:
                        if not any(val in item for val in a['has']):
                            satisfied = False
                            break
                    # compare list with list
                    elif type(item) is list:
                        satisfied = False
                        for i in item:
                            if any(val in i for val in a['has']):
                                satisfied = True
                if satisfied:
                    result.append(report(tactic, t, s_name, p, s, evidence, tool))
                    detected = True
                    break
            # for normal ('or') condition
            else:
                item = s.get(p['key'], '(null)')
                # compare str with list
                if type(item) is str:
                    if any(val in item for val in p['has']):
                        result.append(report(tactic, t, s_name, p, s, evidence, tool))
                        detected = True
                        break
                # compare list with list
                elif type(item) is list:
                    for i in item:
                        if detected:
                            break
                        if any(val in i for val in p['has']):
                            result.append(report(tactic, t, s_name, p, s, evidence, tool))
                            detected = True
                            break

def detect():
    print('[*] Detecting evidence')
    # load rules
    with open('./rule.json', 'r') as rule_file:
        rule = json.load(rule_file)
        for tactic in rule:
            for t in tactic['technique']:
                # detection start
                if 'detection' in t:
                    for d in t['detection']:
                        # find all source files
                        for s in d['source']:
                            # iterate through all source files
                            for s_name in glob.glob(evidence_output_path + s):
                                with open(s_name, 'r') as s_file:
                                    match(json.load(s_file), d['pattern'], tactic['tactic'], t, s_name, d['evidence'], d['tool'])
    # save report
    with open(report_output_path + 'report.json', 'w') as report_file:
        json.dump(result, report_file, indent=2)
        print(f'    [+] Save as \'{report_file.name}\'')

def generate_graph_data():
    print('[*] Generating graph data')
    # initialize data structure
    data = {}
    data['nodes'] = []
    data['links'] = []
    # process level 0 node (sample)
    tmp = {}
    tmp['id'] = task['id']
    tmp['level'] = 0
    tmp['name'] = task['name']
    data['nodes'].append(tmp)
    # create sets
    level_1_set = set()
    level_2_set = set()
    level_3_set = set()
    link_set = set()
    # process result
    for r in result:
        level_1_set.add((r['id'].replace('.', 'o'), f'{r["id"]} {r["name"]}'))
        level_2_set.add(r['evidence'])
        level_3_set.add(r['tool'])
        link_set.add((task['id'], r['id'].replace('.', 'o')))
    # create lists from sets
    level_1_list = list(level_1_set)
    level_2_list = list(level_2_set)
    level_3_list = list(level_3_set)
    # process level 1 nodes (techniques)
    level_1_list.sort()
    for s in level_1_list:
        tmp = {}
        tmp['id'] = s[0]
        tmp['name'] = s[1]
        tmp['level'] = 1
        data['nodes'].append(tmp)
    # process level 2 nodes (evidence)
    ev_map = {}
    count = 0
    level_2_list.sort()
    for s in level_2_list:
        _id = f'EV{count:04}'
        ev_map[s] = _id
        tmp = {}
        tmp['id'] = ev_map[s]
        tmp['name'] = s
        tmp['level'] = 2
        data['nodes'].append(tmp)
        count += 1
    # process level 3 nodes (tools)
    tl_map = {}
    count = 0
    level_3_list.sort()
    for s in level_3_list:
        _id = f'TL{count:04}'
        tl_map[s] = _id
        tmp = {}
        tmp['id'] = tl_map[s]
        tmp['name'] = s
        tmp['level'] = 3
        data['nodes'].append(tmp)
        count += 1
    # add links between evidence and tools
    for r in result:
        link_set.add((r['id'].replace('.', 'o'), ev_map[r['evidence']]))
        link_set.add((tl_map[r['tool']], ev_map[r['evidence']]))
    # process links
    for s in link_set:
        tmp = {}
        tmp['source'] = s[0]
        tmp['target'] = s[1]
        data['links'].append(tmp)
    # save graph data
    with open(report_output_path + 'data.js', 'w') as data_file:
        data_file.write(f'var data = {json.dumps(data, indent=2)};')
        print(f'    [+] Save as \'{data_file.name}\'')

def open_graph():
    print('[*] Opening graph in the browser')
    # copy graph data
    cmd = ['cp', report_output_path + 'data.js', '.']
    subprocess.run(cmd)
    # open in browser
    webbrowser.open('file://' + os.path.realpath('./index.html'))

def filter_artifacts():
    print('[*] Filtering artifacts')
    # load filters
    with open('./filter.json', 'r') as filter_file:
        filters = json.load(filter_file)
        for f in filters:
            f_data = []
            f_names = glob.glob(evidence_output_path + f['path'])
            f_names.sort()
            for f_name in f_names:
                with open(f_name, 'r') as f_file:
                    f_data.append(json.load(f_file))
            f_diff = []
            # compare each entry (before and after)
            for i in f_data[1]:
                origin = copy.deepcopy(i)
                found = False
                for j in f_data[0]:
                    # remove irrelevant attributes
                    for k in f['ignore']:
                        i.pop(k, None)
                        j.pop(k, None)
                    if i == j:
                        found = True
                        break
                if not found:
                    f_diff.append(origin)
            # save diff
            with open(evidence_output_path + f['path'].replace('*', ' diff'), 'w') as diff_file:
                json.dump(f_diff, diff_file, indent=2)
                print(f'    [+] Save as \'{diff_file.name}\'')

def main():
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True,
            help='set task json file',
            action='store', dest='task')
    global args
    args = parser.parse_args()
    # create output folders
    if not os.path.exists('./evidence'):
        os.makedirs('./evidence')
    if not os.path.exists('./reports'):
        os.makedirs('./reports')
    # load task file
    with open(args.task) as task_file:
        global task
        task = json.load(task_file)
    # create task output folder with datetime
    suffix = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H_%M_%SZ')
    global evidence_output_path
    evidence_output_path = f'./evidence/{task["name"]} {suffix}/'
    if not os.path.exists(evidence_output_path):
        os.makedirs(evidence_output_path)
    global report_output_path
    report_output_path = f'./reports/{task["name"]} {suffix}/'
    if not os.path.exists(report_output_path):
        os.makedirs(report_output_path)
    # set tool path
    global collector_path
    collector_path = task['collector']
    global monitor_path
    monitor_path = task['monitor']
    # routine
    start_vm()
    collector()
    copy_task_files()
    monitor()
    run_task()
    time.sleep(int(task['time']))
    #suspend_vm()
    #copy_memory()
    #resume_vm()
    collector()
    copy_artifacts()
    copy_logs()
    filter_artifacts()
    detect()
    generate_graph_data()
    open_graph()

if __name__ == '__main__':
    main()
