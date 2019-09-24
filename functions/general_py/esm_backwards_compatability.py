"""
Backwards compatability for old runscripts
"""
# Python 2 and 3 version agnostic compatiability:
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

# Python Standard Library imports
import logging
import os
import subprocess


FUNCTION_PATH = os.path.dirname(__file__) + "/../"


class ShellscriptToUserConfig(dict):
    """
    Generates a User Config from an old Shellscript
    """

    def __init__(self, runscript_path):
        with open(runscript_path) as runscript_file:
            all_lines = runscript_file.readlines()
        hashbang = all_lines[0]
        bad_lines = ("load_all_functions", "general_do_it_all", "#", "set ")
        good_lines = [
            line.strip() for line in all_lines if not line.startswith(bad_lines)
        ]
        good_lines.insert(0, hashbang)
        good_lines.insert(1, "set -a")
        # Module commands:
        module_commands = [line for line in good_lines if "module" in line]
        # Find index of a command "module purge"
        if "module purge" in module_commands:
            # Anything before module purge is probably irrelevant, so flip the
            # list around first before figuring out which index it is:
            index = module_commands[::-1].index("module purge")
            remaining_module_commands = module_commands[::-1][:index][::-1]
        else:
            remaining_module_commands = module_commands
        module_commands = [l for l in remaining_module_commands if "list" not in l]
        for module_command in module_commands:
            os.system(module_command)
        env_before = os.environ
        logging.debug("Got environment from the system %s", env_before)
        with open("cleaned_runscript", "w") as cleaned_runscript:
            for line in good_lines:
                cleaned_runscript.write(line + "\n")
            logging.debug("Finished writing cleaned_runscript")
        command_to_run = "source %s/cleaned_runscript; env" % os.getcwd()
        logging.debug(
            "Using the following command to determine environment in runscript: %s",
            command_to_run,
        )
        pipe1 = subprocess.Popen(command_to_run, stdout=subprocess.PIPE, shell=True)
        output = pipe1.communicate()[0].decode("utf-8")
        logging.debug(output)
        env_after = {}
        for line in output.split("\n"):
            if line and "=" in line:
                key, value = line.split("=", 1)
                if value:
                    env_after[key] = value
        os.remove("cleaned_runscript")
        diffs = list(set(env_after) - set(env_before))

        known_setups_and_models = os.listdir(FUNCTION_PATH)
        user_config = {}
        logging.debug(diffs)
        solved_diffs = []
        for thisdiff in diffs:
            logging.debug("thisdiff=%s", thisdiff)
            for sim_thing in known_setups_and_models:
                diff_name = thisdiff.replace("_" + sim_thing, "").replace(
                    sim_thing + "_", ""
                )
                user_config.setdefault(sim_thing, {})

                if thisdiff.endswith(sim_thing):
                    user_config[sim_thing][diff_name] = env_after[thisdiff]
                    solved_diffs.append(thisdiff)
                    break
                if thisdiff.startswith(sim_thing):
                    user_config[sim_thing][diff_name] = env_after[thisdiff]
                    solved_diffs.append(thisdiff)
                    break
        user_config = {k: v for k, v in user_config.items() if v}
        for solved_diff in solved_diffs:
            diffs.remove(solved_diff)

        solved_diffs = []
        deprecated_diffs = [
            "FUNCTION_PATH",
            "FPATH",
            "machine_name",
            "ESM_USE_C_CALENDAR",
        ]
        user_config["general"] = {}
        for diff in diffs:
            if diff in deprecated_diffs:
                logging.warning(
                    "You used a discontinued variable: %s. Please reconsider your life choices",
                    diff,
                )
            if diff not in deprecated_diffs:
                user_config["general"][diff] = env_after[diff]
                solved_diffs.append(diff)

        for solved_diff in solved_diffs:
            diffs.remove(solved_diff)
        logging.debug("Diffs after removing: %s", diffs)

        for key, value in user_config.items():
            self.__setitem__(key, value)
