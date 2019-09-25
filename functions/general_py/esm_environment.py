
#!/usr/bin/env python
# import fileinput, os, sys, getopt

import sys, copy, os, re
FUNCTION_PATH = os.path.abspath(os.path.dirname(__file__) + "/../")
sys.path.append(FUNCTION_PATH+"/external_py/coloredlogs")
sys.path.append(FUNCTION_PATH+"/external_py/f90nml")
sys.path.append(FUNCTION_PATH+"/external_py/humanfriendly")
sys.path.append(FUNCTION_PATH+"/external_py/six")
sys.path.append(FUNCTION_PATH+"/external_py/tqdm")
import esm_parser




######################################################################################
########################### class "environment_infos" ################################
######################################################################################

class environment_infos:
    def __init__(self):
        self.machine_file=esm_parser.determine_computer_from_hostname()
        self.config = esm_parser.yaml_file_to_dict(self.machine_file)
    

    def write_dummy_script(self):
        with open("dummy_script.sh", "w") as script_file:
            script_file.write("# Dummy script generated by esm-tools, to be removed later: \n")
            if "module_actions" in self.config:
                for action in self.config["module_actions"]:
                    script_file.write("module "+action+"\n")
            script_file.write("\n")
            if "export_vars" in self.config:
                for var in self.config["export_vars"].keys():
                    script_file.write("export "+var+"="+self.config["export_vars"][var]+"\n")
            script_file.write("\n")

    def add_commands(self, commands, name):
        with open(name+"_script.sh", "w") as newfile:
            with open("dummy_script.sh", "r") as dummy_file:
                newfile.write(dummy_file.read())
            for command in commands:
                newfile.write(command + "\n")
        return name+"_script.sh"


