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

def run_commands_on_instances(ec2Manager, commands_for_instances):
    node_threads = []
    instance_ids = []
    for instance_id, commands in commands_for_instances:
        instance_ids.append(instance_id)
        node_thread = threading.Thread(target=ec2Manager
            .execute_command_on_instance, args=[instance_id, commands])
        node_thread.start()
        node_threads.append(node_thread)

    print ">>> COMMANDS TRIGGERED, WAITING FOR COMPLETION <<<"
    for node_thread in node_threads:
        node_thread.join()

    print ">>> COMMANDS COMPLETED, WAITING FOR OUTPUT <<<"
    time.sleep(ec2Manager.config.SLEEP_TIMEOUT_IN_SECONDS)
    display_output(ec2Manager, instance_ids)

def get_viff_commands(instance_ids, instance_ips, viff_app):
    n = len(instance_ids)
    port_numbers = [9000+i for i in range(1, n + 1)]
    commands_for_instances = []
    kill_command = "killall python"
    for player_number, instance_id in zip(range(1, n + 1), instance_ids):
        viff_config_command = ("python ~/viff/apps/generate-config-files.py " +
                "-n " + str(n) + " -t 1")
        for port_number, instance_ip in zip(port_numbers, instance_ips):
            viff_config_command += " " + instance_ip+":"+str(port_number)

        viff_app_command = ("python ~/viff/apps/" + viff_app +" --no-ssl " +
                "--statistics --deferred-debug player-" + str(player_number) +
                ".ini > output")
        # print(viff_config_command)
        # print(viff_app_command)
        all_commands = [kill_command, viff_config_command,
                            viff_app_command]
        commands_for_instances.append([instance_id, all_commands])
    return commands_for_instances


def get_avss_commands(config, config_json, instance_ids):
    ids = list(config.nodes.keys())
    ids = sorted(ids)
    new_config_json = json.dumps(config_json)
    create_config = "echo '" + new_config_json + "' > ~/new_config.json"
    kill_command = "killall python"
    build_charm_commands = ("pushd ~/charm; sudo ./configure.sh; sudo make; " +
                            "sudo make install; sudo ldconfig; popd")
    commands_for_instances = []
    for instance_id, id in zip(instance_ids, ids):
        command = ("python ~/asyncmix/TestAvssMultipleProcesses.py " +
                        "~/new_config.json " + str(id) + " > ~/output")

        commands = [kill_command, build_charm_commands, create_config, command]
        commands_for_instances.append([instance_id, commands])
    return commands_for_instances


def get_hbavss_commands(config, config_json, instance_ids):
    ids = list(config.nodes.keys())
    instance_ids.append(instance_ids[0])
    del instance_ids[0]
    new_config_json = json.dumps(config_json)
    create_config = "echo '" + new_config_json + "' > ~/new_config.json"
    kill_command = "killall python"
    build_charm_commands = ("pushd ~/charm; sudo ./configure.sh; sudo make; " +
                            "sudo make install; sudo ldconfig; popd")
    commands_for_instances = []
    for instance_id, id in zip(instance_ids, ids):
        command = ("python ~/asyncmix/TestHbAvssMultipleProcesses.py " +
                        "~/new_config.json " + str(id) + " > ~/output")
        commands = [kill_command, build_charm_commands, create_config, command]

        commands_for_instances.append([instance_id, commands])

    return commands_for_instances


def update_json_with_ips(instance_ips, config_json, total_vms):
    config_json["Dealer"]["Ip"] = instance_ips[0]
    assert len(instance_ips) == len(config_json["Recipients"])+1
    for recipient, ip in zip(config_json["Recipients"], instance_ips[1:]):
        recipient["Ip"] = ip
    return config_json


ec2Manager = EC2Manager()
if len(sys.argv) == 2:
    config_path = sys.argv[1]
    config = Config(config_path)
    total_vms = len(config.nodes.keys())
    instance_ids, instance_ips = ec2Manager.create_instances(total_vms)
    config_json = update_json_with_ips(instance_ips, config.json, total_vms)
    config.prepare_config_object(config_json)

    if config.is_hbavss:
        print "Running HBAVSS"
        commands_for_instances = get_hbavss_commands(config, config_json,
            instance_ids)
    else:
        print "Running AVSS"
        commands_for_instances = get_avss_commands(config, config_json,
            instance_ids)
elif ec2Manager.config.MPC_FRAMEWORK == "viff":
    print "Running VIFF"
    instance_ids, instance_ips = ec2Manager.create_instances()
    commands_for_instances = get_viff_commands(instance_ids, instance_ips,
        ec2Manager.config.MPC_APP_NAME)

run_commands_on_instances(ec2Manager, commands_for_instances)
