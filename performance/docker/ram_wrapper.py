import argparse
import json
import logging.config
import random
import re
import subprocess
import time
import uuid
import threading
import multiprocessing
import os

def run_child_file():
    # Import and execute the child Python file
    import docker_stats

def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]

def run(log, browser, configurations, domains, cpu):
    random.shuffle(domains)
    for domain in domains:
        # We always visit with the website without any extensions first to
        # warm up the upstream DNS cache.
        # run_configuration(log, browser, "", domain, cpu)

        random.shuffle(configurations)
        for extension in configurations:
            run_configuration(log, browser, extension, domain, cpu)

def run_configuration(log, browser, extension, domain, cpu):
    log.info(f"Collecting mpstat data via {browser} with '{extension}' for '{domain}' on cpu '{cpu}'")
    try:
        get_domain(log, browser, extension, domain, cpu)

    except Exception as e:
        log.error(f"Unknown error for domain '{domain}': {e}")

def get_domain(log, browser, extension, domain, cpu):
    try:
        strip_domain = domain.split('//')
        if len(strip_domain) == 2:
            container_name = f'{extension}_{strip_domain[1]}'
        else:
            container_name = f'{extension}_{strip_domain[0]}'
        
        env_var = f'CUSTOM_CMD=python3 /home/seluser/measure/ram.py "--extensions" {extension} --cpu {cpu} {domain}'
        cmd = ["docker", "run", "--name", container_name,
                "--rm", "-m", "4g",
                "-v", "/dev/shm:/dev/shm",
                "-v", "./chrome/data:/data",
                "--cpuset-cpus", cpu,
               "--security-opt", "seccomp=./seccomp.json",
               "-e", env_var,
               f"mpstat-{browser}"]
        # we can use "--shm-size=2g" instead of /dev/shm:/dev/shm
        run = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Error in container for '{domain}': {e.output}")
    
    stdout = run.stdout.decode('utf-8')
    stderr = run.stderr.decode('utf-8')
    print('STDOUT:', stdout) 
    print('STDERR:', stderr)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('log', default="logs/measurement.log")
    #parser.add_argument('database_config_file')
    parser.add_argument('domains_list_file')
    parser.add_argument('cpus')
    parser.add_argument('browser')
    args = parser.parse_args()

    logging.basicConfig(filename=args.log, level=logging.DEBUG)
    log = logging.getLogger('wrapper')

    #database = Database.init_from_config_file(args.database_config_file)

    if args.browser not in ('firefox', 'chrome'):
        raise ValueError(f"Browser must be 'firefox' or 'chrome', not '{args.browser}'")

    domains = []
    # domains = ['http://www.google.com']
    with open(args.domains_list_file, 'r') as f:
        inner_dict = json.load(f)
        for key in inner_dict:
            domains.append(inner_dict[key][0])
            # if len(domains) == 500:
            #     break
    f.close()

    extensions_configurations = [
       # No extensions
       "control",
       # Extensions on their own
       "adblock",
       "decentraleyes",
       "disconnect",
       "ghostery",
       "privacy-badger",
       "ublock",
       "adguard"
    # Combinations
    #    "decentraleyes,privacy_badger,ublock_origin"
    ]


    # RUNNING 4 DOCKERS ON 4 DIFFERENT CPU CORES
    cpus_list = [str(cpu) for cpu in range(int(args.cpus))]
    thread_list = []
    domain_set = list(divide_chunks(domains, int(len(domains)/len(cpus_list))))
    print(domain_set)
    for i in range(len(cpus_list)):
        # thread_list.append(threading.Thread(target=run, args=(log, args.browser, extensions_configurations, domain_set[i], cpus_list[i],)))
        thread_list.append(multiprocessing.Process(target=run, args=(log, args.browser, extensions_configurations, domain_set[i], cpus_list[i],)))
    
    # subprocess.Popen(["python3", "docker_stats.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.PIPE)

    log.info("starting threads ....")
    for thread in thread_list:
        log.info(f"Starting run for '{thread}'")
        start_time = time.time()
        print('thread starts')
        thread.start()
        log.info(f"Elapsed time: {time.time() - start_time} seconds for '{thread}'")

    log.info("joining threads ....")
    for thread in thread_list:
        print('thread joins')
        thread.join()


if __name__ == '__main__':
    child_process = multiprocessing.Process(target=run_child_file)
    child_process.start()
    main()


