#!/usr/bin/env python3
#Reference: https://raw.githubusercontent.com/CoreyMSchafer/code_snippets/master/Python/Matplotlib/09-LiveData/finished_code.py
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os
import psutil
import sys
from collections import defaultdict
import time

plt.style.use('fivethirtyeight')

#Global variables to store data for access by animate()
#The two dicts below map pids to a list of memory usage recorded at each interval
mem_usage = defaultdict(list)
cpu_usage = defaultdict(list)

dead_pids = set()
intervals = []
done = False
start = time.time()
ppid = 0
peak_usage = 0 
reimann_sum = 0

def animate(i):
    global mem_usage
    global cpu_usage
    global alive_pids
    global dead_pids
    global intervals
    global done
    global ppid
    global peak_usage
    global reimann_sum

    if not alive_pids:
        return

    #If a single pid was provided, it is the parent
    if not ppid and len(pids) == 1:
        ppid = pids[0]


    #Update alives in case new children have been spawned
    new_children = []
    for pid in alive_pids:
        try:
            current_process = psutil.Process(pid)
            new_children += [child.pid for child in current_process.children(recursive=True)]
        except psutil.NoSuchProcess:
            print(f"Seems that {pid} has died.")
            dead_pids.add(pid)
            continue
        except Exception as e:
            print(f"Error recursing over child processes {e}")
    alive_pids = alive_pids.union(set(new_children)) - dead_pids
    
    #print('Child pid is {}'.format(child.pid))

    #Get mem usage of every alive process
    for pid in alive_pids:
        try:
            alive_process = psutil.Process(pid)
            this_mem_usage = alive_process.memory_full_info()[1] / (1000**2)
            mem_usage[pid].append(this_mem_usage)
            print(f"Set mem usage for  pid {pid}: {this_mem_usage}")
        except psutil.NoSuchProcess:
            print(f"Seems that {pid} has died.")
            #alive_pids.remove(pid)
            dead_pids.add(pid)
        except Exception as e:
            print(f"{e}")
            sys.exit(1)
    alive_pids = alive_pids - dead_pids

    #Dead processes don't use memory
    for pid in dead_pids:
        mem_usage[pid].append(0)

    #Set stop flag if all processes are dead
    if not alive_pids:
        print("All processes have died.  Stopping.  You may wish to save the plot.")
        done = True

    #Update the intervals
    intervals.append(time.time()-start)
            
    #Clear and redraw plot
    plt.cla()
    instant_usage = 0
    for pid, usage in mem_usage.items():
        instant_usage += usage[-1]
        if pid and ppid == pid:
            label = "Parent: "
        else: label = "Child: "
        #print(f"plot {intervals} vs {usage}")
        plt.plot(intervals[-len(usage):], usage, label = f"{label} {pid}")
    peak_usage = max(instant_usage, peak_usage)
    reimann_sum += instant_usage

    plt.title(f"Memory Usage for {proc_name}\nCurrent: {round(instant_usage)}\nPeak: {round(peak_usage,2)} MB\nMB-Seconds:{round(reimann_sum)}")
    plt.legend(loc='upper left')
    plt.tight_layout()


#Function below copied from https://thispointer.com/python-check-if-a-process-is-running-by-name-and-find-its-process-id-pid/
def findProcessIdByName(processName):
    '''
    Get a list of all the PIDs of a all the running process whose name contains
    the given string processName
    '''
 
    listOfProcessObjects = []
 
    #Iterate over the all the running process
    for proc in psutil.process_iter():
       try:
           pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
           # Check if process name contains the given name string.
           if processName.lower() in pinfo['name'].lower() :
               listOfProcessObjects.append(pinfo)
       except (psutil.NoSuchProcess, psutil.AccessDenied , psutil.ZombieProcess) :
           pass
 
    return [p['pid'] for p in listOfProcessObjects]

def data_gen():
    b = 0
    while not done:
        b += 1
        yield b

if __name__ == "__main__":
    global alive_pids 
    if len(sys.argv) != 2:
        print("Must provide a pid or process name")
        sys.exit(1)

    pid = 0
    pids = []
    proc_name = ""

    try:
        pid = int(sys.argv[1]) 
    except ValueError:
        proc_name = sys.argv[1]

    #If a pid was given, is it a valid pid?
    if pid:
        if psutil.pid_exists(pid):
            print(f"Found process with pid: {pid}")
            proc_name = psutil.Process(pid).name
        else:
            print(f"No process with pid'{pid}' found.  Exiting.")
            sys.exit(1)    

    #Otherwise I assume a process name was given:
    else:
    #Try to get all pids of matching processes
        while True:
            pids = findProcessIdByName(proc_name)
            if pids:
                print(f"PIDs for processes matching '{proc_name}':\n{pids}")
                break
            else:
                print(f"No process(es) '{proc_name}' found.  Waiting for such process to start...")
                time.sleep(3)

    #Pass pid(s) via a global set, so make a list if only one was given
    if pid:
        pids = [pid]
    alive_pids = set(pids)

    ani = FuncAnimation(plt.gcf(), animate, frames=data_gen, interval=3000, repeat=False)

    plt.tight_layout()
    plt.show()
