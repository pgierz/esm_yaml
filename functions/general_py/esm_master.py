#!/usr/bin/env python
# import fileinput, os, sys, getopt
import sys, copy, os
import esm_parser


######################################################################################
##################################### globals ########################################
######################################################################################




#model_kinds=["setups", "couplings", "components"]
#known_todos = ["get", "conf", "comp", "clean", "status", "update", "install"]
#compile_order = ["get", "conf", "comp"]
#known_repos = ["git", "svn"]
#vcs_todos=["get", "status", "update", "install"]
#basic_infos= { "GITLAB_USER_NAME": ("User name on gitlab.dkrz.de", "anonymous") }
#display_kinds=['setups', 'components', 'couplings']


components_yaml='functions/setups2models.yaml'
config_yaml='functions/esm_master.yaml'
vcs_folder='functions/vcs'

overall_conf_file='~/.esm_master.conf'
local_conf_file='esm_master.conf'

#verbose=True
verbose=False


######################################################################################
############################## class "general_infos" #################################
######################################################################################


class general_infos:
    def __init__(self):

        self.config = esm_parser.yaml_file_to_dict(config_yaml)
        self.emc = self.read_and_update_conf_files()
        self.meta_todos, self.meta_command_order = self.get_meta_command()
        self.display_kinds = self.get_display_kinds()


        if verbose:
            self.output()                    


    def read_and_update_conf_files(self):
        complete=True
        emc = {}
        for conffile in [overall_conf_file, local_conf_file]:
            if os.path.isfile(conffile):
                with open(conffile) as myfile:
                    for line in myfile:
                        name, var = line.partition("=")[::2]
                        emc[name.strip()] = var.strip()
        if "basic_infos" in self.config.keys():
            for basic_info in self.config["basic_infos"]:
                question = self.config["basic_infos"][basic_info]["question"]
                default = self.config["basic_infos"][basic_info]["default"]
                if not basic_info in emc.keys():
                    if complete:
                        print ("The configuration files are incomplete or non-existent.")
                        print ("Please answer the following questions to configure esm-tools:")
                        print ("(Hit enter to accept default values.)")
                        complete=False
                    user_input = input(question + " (default = " + default + "): ")
                    if user_input.strip() == "":
                        user_input = default
                    emc.update({basic_info.strip(): user_input.strip()})
        if not complete:
            with open(local_conf_file, "w") as new_conf_file:
                for oldentry in emc.keys():
                    new_conf_file.write(oldentry+"="+emc[oldentry]+"\n")
        return emc


    def get_meta_command(self):
        meta_todos = []
        meta_command_order = {}
        for entry in self.config:
            if entry.endswith("_meta_command"):
                todo = entry.replace("_meta_command", "")
                meta_todos.append(todo)
                meta_command_order.update({todo: self.config[entry]})
        return meta_todos, meta_command_order


    def get_display_kinds(self):
        if "display_kinds" in self.config.keys():
            return self.config["display_kinds"]

    def output(self):
        print()
        for key in self.emc:
            print (key+": "+str(self.emc[key]))
        print ("Meta commands: ")
        for key in self.meta_command_order:
            print ("    "+key+": "+str(self.meta_command_order[key]))





######################################################################################
########################### class "version_control_infos" ############################
######################################################################################


class version_control_infos:
    def __init__(self):
        self.config={}
        vcs_files = [f for f in os.listdir(vcs_folder)]
        self.known_repos=[]
        for vcs_file in vcs_files:
            if os.path.isfile(vcs_folder+"/"+vcs_file):
                repo_type = vcs_file.replace(".yaml", "")
                self.config.update({repo_type: esm_parser.yaml_file_to_dict(vcs_folder+"/"+vcs_file)})
                self.known_repos.append(repo_type)
        self.known_todos=[]
        for repo in self.known_repos:
            for entry in self.config[repo].keys():
                if entry.endswith("_command"):
                    todo = entry.replace("_command", "")
                    if todo not in self.known_todos:
                        self.known_todos.append(todo)
        if verbose:
            self.output()

    def assemble_command(self, package, todo, setup_info):
        if package.repo_type and package.repo:
            if todo in setup_info.meta_todos:
                return None
            try:
                raw_command=self.config[package.repo_type][todo+"_command"]
                if package.branch:
                    define_branch = self.config[package.repo_type]["define_branch"]
                    raw_command = raw_command.replace("${define_branch}", define_branch)
                    raw_command = raw_command.replace("${branch}", package.branch)
                else:
                    raw_command = raw_command.replace("${define_branch} ", "")
                    raw_command = raw_command.replace("${branch}", "")

                if package.tag:
                    define_tag = self.config[package.repo_type]["define_tag"]
                    raw_command.replace("${define_tag}", define_tag) 
                    raw_command.replace("${tag}", package.tag)
                else:
                    raw_command = raw_command.replace("${define_tag} ", "")
                    raw_command = raw_command.replace("${tag}", "")
            except:
                print ("Sorry, no "+todo+"_command defined for "+package.repo_type)
                sys.exit(42)
            if type(package.repo) == list:
                repo=package.repo[0]
            else:
                repo=package.repo
            raw_command = raw_command.replace("${repository}", repo)
        else:
            raw_command = None
        return raw_command

    def output(self):
        print()
        esm_parser.pprint_config(self.config)
        print ("Known repos: " + str(self.known_repos))
        print ("Known vcs-commands: " + str(self.known_todos))















######################################################################################
############################## class "software_package" ##############################
######################################################################################


class software_package:
    def __init__(self, raw, setup_info, vcs, no_infos=False):# model_and_version):
        if type(raw) == str:
            dummy, self.kind, self.model, self.version, dummy2, self.raw_name = setup_info.split_raw_target(raw, setup_info)
        else: #tupel:
            (self.kind, self.model, self.version) = raw
            self.raw_name = setup_info.assemble_raw_name(None, self.kind, self.model, self.version)

        self.tag=None
        if not no_infos:
            self.fill_in_infos(setup_info, vcs)
        else:
            self.targets=self.subpackages=None
            self.repo_type = self.repo = self.branch = None
            self.bin_type = None
            self.bin_names = [None]
            self.command_list = None

    def fill_in_infos(self, setup_info, vcs):
        self.targets = self.get_targets(setup_info, vcs)
        self.subpackages = self.get_subpackages(setup_info, vcs)
        self.complete_targets(setup_info)
        self.repo_type, self.repo, self.branch = self.get_repo_info(setup_info, vcs)
        self.bin_type, self.bin_names = self.get_comp_type(setup_info)
        self.command_list = self.get_command_list(setup_info, vcs)

    def get_targets(self, setup_info, vcs):
        config = setup_info.config
        targets = []
        for todo in setup_info.known_todos:
            if setup_info.has_target(self, todo, vcs):
                targets.append(todo)    
        return targets

    def complete_targets(self, setup_info):
        for todo in setup_info.known_todos:
            for package in self.subpackages:
                if todo in package.targets:
                    if todo not in self.targets:
                            self.targets.append(todo)

    def get_subpackages(self, setup_info, vcs):
        subpackages=[]
        config = setup_info.config
        if self.kind == "couplings":
            components = setup_info.get_config_entry(self, "components")
            if components:
                for component in components:
                    comp_tupel = software_package(component, setup_info, vcs)
                    if comp_tupel not in subpackages:
                        subpackages.append(comp_tupel)
        elif self.kind == "setups":
            couplings = setup_info.get_config_entry(self, "couplings")
            if couplings:
                for coupling in couplings: 
                    for component in config["couplings"][coupling]["components"]:
                        found = False
                        for package in subpackages:
                            if component == package.raw_name:
                                found = True
                                break
                        if not found:    
                            subpackages.append(software_package(component, setup_info, vcs))
        return subpackages

    def get_comp_type(self, setup_info):
        exec_names = setup_info.get_config_entry(self, "install_bins")
        if exec_names:
            if type(exec_names) == str:
                exec_names=[exec_names]
            return "bin", exec_names
        exec_names = setup_info.get_config_entry(self, "install_libs")
        if exec_names:
            if type(exec_names) == str:
                exec_names=[exec_names]
            return "lib", exec_names
        return "bin", []

    def get_repo_info (self, setup_info, vcs):
        repo = branch = repo_type = None
        for check_repo in vcs.known_repos:
            repo = setup_info.get_config_entry(self, check_repo+"-repository")
            if repo:
                repo_type = check_repo
                break
        branch = setup_info.get_config_entry(self, "branch")
        return repo_type, repo, branch

    def get_command_list(self, setup_info, vcs):
        command_list={}
        for todo in self.targets:
            if todo in vcs.known_todos:
                commands = vcs.assemble_command(self, todo, setup_info)
            else:
                commands = setup_info.get_config_entry(self, todo+"_command")
            if commands:
                if type(commands) == str:
                    commands = [commands]
                if not todo == "get":
                    commands.insert(0, "cd "+self.raw_name)
                    commands.append("cd ..")
            command_list.update({todo: commands})
        return command_list

    def output(self):
        print ()
        print (self.raw_name)
        print ("    Model:", self.model, ", Version:", self.version, ", Kind:", self.kind)
        if self.subpackages:
            for package in self.subpackages:
                print ("    Subpackage: ", package.raw_name)
        if self.targets:
            print ("    Targets: ", self.targets)
        if self.repo_type:
            print ("    Repo_type: ", self.repo_type, ", repo: ", self.repo, ", branch: ", self.branch) 
        if self.bin_type:
            print ("    Bin_type: ", self.bin_type, ", bin_names: ", self.bin_names) 
        if self.command_list:
            print ("    Commands:")
            for todo in self.command_list.keys():
                print ("        ", todo, self.command_list[todo])
    




######################################################################################
################################# class "task" #######################################
######################################################################################



class task:
    def __init__(self, raw, setup_info, vcs):
        if type(raw) == list:
            str_arg = ""
            for arg in raw:
                str_arg=str_arg + " " + arg
            raw = str_arg.strip()
            if raw == "default":
                raw = ""
            if raw == "drytestall":
                # panic
                for package in setup_info.all_packages:
                    for todo in package.targets:
                        try:
                            print (todo+"-"+package.raw_name)
                            newtask = task(todo+"-"+package.raw_name, setup_info, vcs)
                            newtask.output_steps()  
                        except:
                            print ("Problem found with target "+newtask.raw_name)
                            sys.exit(1)
                sys.exit(0)
        
        if type(raw) == str:
            self.todo, kind, model, version, self.only_subtask, self.raw_name = setup_info.split_raw_target(raw, setup_info)
            self.package = software_package((kind, model, version), setup_info, vcs)
        else: #tupel:
            (self.todo, kind, model, version, self.only_subtask) = raw
            self.package = software_package((kind, model, version), setup_info, vcs)
            self.raw_name = setup_info.assemble_raw_name(self.todo, kind, model, version)

        if not self.todo in setup_info.meta_todos:
            self.check_if_target(setup_info)

        self.subtasks=self.get_subtasks(setup_info, vcs)
        self.only_subtask=self.validate_only_subtask()
        self.ordered_tasks=self.order_subtasks(setup_info)
        self.will_download = self.check_if_download_task(setup_info)
        self.folders_after_download=self.download_folders()
        self.binaries_after_compile=self.compile_binaries()
        self.dir_list=self.list_required_dirs()
        self.command_list=self.assemble_command_list()

        if verbose:
            self.output()


    def get_subtasks(self, setup_info, vcs):
        subtasks = []
        if self.todo in setup_info.meta_todos:
            todos = setup_info.meta_command_order[self.todo]
        else:
            todos = [self.todo]
        for todo in todos:    
            for subpackage in self.package.subpackages:
                if todo in subpackage.targets:
                    subtasks.append(task((todo, subpackage.kind, subpackage.model, subpackage.version, None), setup_info, vcs))
        if subtasks == [] and self.todo in setup_info.meta_todos:
            for todo in todos:
                if todo in self.package.targets:
                    subtasks.append(task((todo,self.package.kind, self.package.model, self.package.version, None), setup_info, vcs))
        return subtasks

    def validate_only_subtask(self):
        only=None
        if self.only_subtask:
            only = []
            for task in self.subtasks:
                if task.package.raw_name.startswith(self.only_subtask):
                    only.append(task)
            if only == []:
                print()
                print ("Given subtask "+self.only_subtask+" is not a valid subtask of package "+self.raw_name+".")
                print ()
                sys.exit(0)
        return only

    def order_subtasks(self, setup_info):
        subtasks = self.subtasks
        if self.only_subtask:
            if self.only_subtask == "NONE":
                return []
            elif type(self.only_subtask)==str:
                return [self.only_subtask]
            else:
                subtasks = self.only_subtask
        if subtasks == []:
            return [self]
        if self.todo in setup_info.meta_todos:
            todos = setup_info.meta_command_order[self.todo]
        else:
            todos = [self.todo]

        ordered_tasks = []
        for todo in todos:
            for task in subtasks:
                if task.todo == todo and task.package.bin_type == "lib":
                    ordered_tasks.append(task)
            for task in subtasks:
                if task.todo == todo and not task.package.bin_type == "lib":
                    ordered_tasks.append(task)
        return ordered_tasks


    def check_if_download_task(self, setup_info):
        if self.todo == "get": 
            return True
        if self.todo in setup_info.meta_todos:
            if "get" in setup_info.meta_command_order[self.todo]:
                return True
        return False


    def download_folders(self):
        if self.package.kind in ["setups", "couplings"]:
            dir_list = [self.package.raw_name]
        else:
            dir_list = []
        for task in self.ordered_tasks:
            dir_list.append(self.package.raw_name+"/"+task.package.raw_name)
        return dir_list
    
    def compile_binaries(self):
        file_list = []
        for task in self.ordered_tasks:
            for binfile in task.package.bin_names:
                file_list.append(self.package.raw_name+"/"+task.package.bin_type+"/"+binfile.split("/")[-1])
        return file_list

    def list_required_dirs(self):
        toplevel = self.package.raw_name
        if self.package.kind in ["setups", "couplings"] and self.will_download:
            dir_list = [self.package.raw_name]
        else:
            dir_list = []
        for task in self.ordered_tasks:
            if task.todo == "comp":
                if task.package.bin_names:
                    newdir = toplevel + "/" + task.package.bin_type
                    if not newdir in  dir_list:
                        dir_list.append(newdir)
        return dir_list

    def assemble_command_list(self):
        command_list=[]
        toplevel = self.package.raw_name
        for folder in self.dir_list:
            command_list.append("mkdir -p "+folder)
        if self.package.kind in ["setups", "couplings"]:
            command_list.append("cd "+toplevel)
            toplevel = "."
        for task in self.ordered_tasks:
            for command in task.package.command_list[task.todo]:
                command_list.append(command)
            if task.todo == "comp":
                if task.package.bin_names:
                    for binfile in task.package.bin_names:
                        command_list.append("cp "+toplevel+"/"+task.package.raw_name+"/"+binfile + " "+ toplevel+"/"+task.package.bin_type)
        if self.package.kind in ["setups", "couplings"]:
            command_list.append("cd ..")
        return command_list


    def check_if_target(self, setup_info):
        if not setup_info.has_target2(self.package, self.todo):
            setup_info.output_available_targets(self.raw_name)
            sys.exit(0)


    def check_requirements(self):
        if self.will_download:
            return True
        requirements = self.folders_after_download
        for folder in requirements:
            if not os.path.isfile(folder):
                print ()
                print ("Missing folder "+ folder + " detected. Please run 'make get-"+self.package.raw_name+ "' first.")
                print ()
                sys.exit(0)
        return True


    def validate(self):
        self.check_requirements()
        self.output_steps()    


    def output(self):
        print ()
        subtasklist=[]
        osubtasklist=[]
        self.package.output()
        print ("    Todo: ", self.todo)
        if self.only_subtask:
            if self.only_subtask == "NONE":
                print ("    NO VALID SUBTASKS!!!")
            else:
                for subtask in self.only_subtask:
                    print ("    Only Subtask:", subtask.package.raw_name)
        for subtask in self.subtasks:
            subtasklist.append(subtask.raw_name)
        for osubtask in self.ordered_tasks:
            osubtasklist.append(osubtask.raw_name)
        if not subtasklist == []:    
            print ("    Subtasks:", subtasklist)
        if not osubtasklist == []:    
            print ("    Ordered Subtasks:", osubtasklist)
        self.output_steps()
        if not self.folders_after_download == []:
            print ("    The following folders should exist after download:")
            for folder in self.folders_after_download:
                print ("        ", folder)
        if not self.binaries_after_compile == []:
            print ("    The following files should exist after compiling:")
            for binfile in self.binaries_after_compile:
                print ("        ", binfile)


    def output_steps(self):
        if not self.command_list == []:
            print ("    Executing commands in this order:")
            for command in self.command_list:
                print ("        ", command)




######################################################################################
########################### class "setup_and_model_infos" ############################
######################################################################################



class setup_and_model_infos:
    def __init__(self, vcs, general):
        self.config = esm_parser.yaml_file_to_dict(components_yaml)
        self.model_kinds = list(self.config.keys())
        self.meta_todos=general.meta_todos
        self.meta_command_order = general.meta_command_order
        self.display_kinds = general.display_kinds

        self.model_todos=[]
        for kind in self.model_kinds:
            for model in self.config[kind].keys():
                version=None
                if "choose_versions" in self.config[kind][model]:
                    for version in self.config[kind][model]["choose_versions"]:
                        for entry in self.config[kind][model]["choose_version"][version]:
                            if entry.endswith("_command"):
                                todo = entry.replace("_command", "")
                                if todo not in self.model_todos:
                                    self.model_todos.append(todo)
                for entry in self.config[kind][model]:
                    if entry.endswith("_command"):
                        todo = entry.replace("_command", "")
                        if todo not in self.model_todos:
                            self.model_todos.append(todo)

        self.known_todos = self.model_todos + vcs.known_todos + general.meta_todos
        self.all_packages = self.list_all_packages(vcs)
        self.update_packages(vcs)
        self.output()

        if verbose:
            self.output()

    def update_packages(self, vcs):
        for package in self.all_packages:
            package.fill_in_infos(self, vcs)

    def list_all_packages(self, vcs):
        packages = []
        config=self.config
        for kind in self.model_kinds:
            for model in config[kind]:
                version=None
                if "available_versions" in config[kind][model]:
                    for version in config[kind][model]["available_versions"]:
                        packages.append(software_package((kind,model,version), self, vcs, no_infos=True))
                else: 
                    packages.append(software_package((kind, model, version), self, vcs, no_infos=True))                    
        return packages

    def has_target(self, package, target, vcs):
        if target in vcs.known_todos:
            for repo in vcs.known_repos:
                answer = self.get_config_entry(package, repo+"-repository")
                if answer:
                    return True
        else:
            answer = self.get_config_entry(package, target+"_command")
            if answer:
                return True
        return False

    def has_target2(self, package, target):
        for testpackage in self.all_packages:
            if testpackage.raw_name == package.raw_name and target in testpackage.targets:
                return True
        return False

    def has_package(self, package):
        if package in self.all_packages:
            return True
        else:
            return False

    def has_model(self, model):
        for kind in self.model_kinds:
            for test_model in self.config[kind]:
                if test_model == model:
                    return True
        return False

    def split_raw_target(self, rawtarget, setup_info):
        todo = kind = only_subtarget = None
        model = version = ""
        if "/" in rawtarget:
            rawtarget, only_subtarget = rawtarget.rsplit("/", 1)

        raw = rawtarget
        for this_todo in setup_info.known_todos:
            if rawtarget == this_todo:
                return this_todo, None, None, None, None, raw
            elif rawtarget.startswith(this_todo+"-"):
                todo=this_todo
                rawtarget=rawtarget.replace(todo+"-", "")
                break

        for package in self.all_packages:
            if package.raw_name == rawtarget:
                return todo, package.kind, package.model, package.version, only_subtarget, raw

        # package not found:
        self.output_available_targets(rawtarget)
        sys.exit(0)


    def assemble_raw_name(self, todo, kind, model, version):
        raw = sep = ""
        if todo:
            raw = todo
            sep = "-"
        if model:
            raw = raw + sep + model
            sep = "-"
        if version:
            raw = raw + sep + version
            sep = "-"
        if not raw == "":
            return raw
        return None


    def setup_or_model(self, model):
        kind_of_model = "unknown"
        for kind in self.model_kinds:
            if model in self.config[kind]:
                kind_of_model = kind
        return kind_of_model


    def output_available_targets(self, search_keyword):
        display_info = []
        if search_keyword == "":
            display_info = self.all_packages
        else:
            for package in self.all_packages:
                for target in package.targets:
                    if search_keyword in target+"-"+package.raw_name:
                        if package not in display_info:
                            display_info.append(package)
        
        if display_info == []:
            print ()
            print ("No targets found for keyword "+search_keyword+". Type 'make' to get a full list")
            print ("of available targets.")
            print ()
        elif display_info == self.all_packages:
            print ()
            print ("Master Tool for ESM applications, including download and compiler wrapper functions")
            print ("		originally written by Dirk Barbi (dirk.barbi@awi.de)" )
            print ("       further developed as OpenSource, coordinated and maintained at AWI" )
            print ()
            print ("Obtain from:         https://gitlab.dkrz.de/esm-tools/esm-master.git")
            print ()
            self.print_nicely(display_info)
            print ()
        else:
            print ()
            print (search_keyword+" is not an available target. Did you mean one of those:")
            self.print_nicely(display_info)
            print ()


    def print_nicely(self, display_info):
        sorted_display={}
        for kind in self.display_kinds:
            for package in display_info:
                if package.kind == kind:
                    if not kind in sorted_display.keys():
                        sorted_display.update({kind: {}})
                    if not package.model in sorted_display[kind]:
                        sorted_display[kind].update({package.model: []})
                    if package.version:
                        sorted_display[kind][package.model].append(package.version+": "+str(package.targets))
                    else:
                        sorted_display[kind][package.model].append(str(package.targets))

        for kind in sorted_display.keys():
            print (kind+": ")
            for model in sorted_display[kind]:
                if len(sorted_display[kind][model]) == 1:
                    print ("    "+model+": "+ sorted_display[kind][model][0])
                else:
                    print ("    "+model+": ")
                    for version in sorted_display[kind][model]:
                        print ("       "+version)


    def get_config_entry(self, package, entry):
        try:
            answer = self.config[package.kind][package.model]["choose_version"][package.version][entry]
        except:
            try: 
                answer = self.config[package.kind][package.model][entry]
            except:
                answer = None
        return answer


    def output(self):
        print ()
        print ("Model kinds: " + str(self.model_kinds))
        print ("Model todos: " + str(self.model_todos))
        print ("All known todos: " + str(self.known_todos))
        for package in self.all_packages:
            package.output()














        

















######################################################################################
##################################### MAIN STUFF #####################################
######################################################################################






def main(args):

    main_infos = general_infos()
    vcs = version_control_infos()
    setups2models = setup_and_model_infos(vcs, main_infos)
    user_task = task(args, setups2models, vcs)
    user_task.validate()




   




    sys.exit(0)





if __name__ == "__main__":
    main(sys.argv[1:])
