import time
import os
import threading
import sys
from ec2Manager import EC2Manager
import json

sys.path.append("../")
from HelperClasses import Config

def display_output(ec2Manager, instance_ids):
    for instance_id in instance_ids:
        ec2Manager.execute_command_on_instance(instance_id, ["cat ~/output"],
                True)


def run_avss(ec2Manager, config, config_json, instance_ids):
    ids = list(config.nodes.keys())
    ids = sorted(ids)    
    new_config_json = json.dumps(config_json)
    create_config = "echo '" + new_config_json + "' > ~/new_config.json"
    node_threads = []
    for instance_id, id in zip(instance_ids, ids):
        command = ("python ~/asyncmix/TestAvssMultipleProcesses.py " +
                        "~/new_config.json " + str(id) + " > ~/output")
        build_commands = ("pushd ~/charm; sudo ./configure.sh; sudo make; " +
                            "sudo make install; sudo ldconfig; popd")
        commands = [build_commands, create_config, command]
        node_thread = threading.Thread(target=ec2Manager
            .execute_command_on_instance, args=[instance_id, commands])
        node_thread.start()
        node_threads.append(node_thread)
    
    for node_thread in node_threads:
        node_thread.join()

    time.sleep(ec2Manager.config.SLEEP_TIMEOUT_IN_SECONDS)
    print instance_ids
    display_output(ec2Manager, instance_ids)


def update_json_and_instance_ids(eC2Manager, config, total_vms):
    instance_ids, instance_ips = ec2Manager.create_instances(total_vms)
    config["Dealer"]["Ip"] = instance_ips[0]
    assert len(instance_ips) == len(config["Recipients"])+1
    for recipient, ip in zip(config["Recipients"], instance_ips[1:]):
        recipient["Ip"] = ip
    return config, instance_ids

config = Config("config.json")
total_vms = len(config.nodes.keys())
ec2Manager = EC2Manager()
config_json, instance_ids = update_json_and_instance_ids(ec2Manager, config.json,
                        total_vms)
config.prepare_config_object(config_json)
run_avss(ec2Manager, config, config_json, instance_ids)
