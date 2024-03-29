"""
Documentation goes here
"""
import logging
import os
import pdb
import shutil
import sys
from io import StringIO

import externals
import f90nml
import six
import tqdm
import yaml
import time


from esm_calendar import Date
import esm_parser
import esm_coupler
import esm_methods
from esm_profile import *

import pprint
pp = pprint.PrettyPrinter(indent=4)

def date_representer(dumper, date):
    return dumper.represent_str("%s" % date.output())


yaml.add_representer(Date, date_representer)


class SimulationSetup(object):
    @timing
    def __init__(self, command_line_config):

        user_config = esm_parser.shell_file_to_dict(command_line_config["scriptname"])
        user_config["general"].update(command_line_config)

        self.config = esm_parser.ConfigSetup(user_config["general"]["setup_name"].replace("_standalone",""), user_config)
        
        del user_config

        self.config["computer"]["jobtype"] = self.config["general"]["jobtype"]
        
        self._read_date_file(self.config)
        self._initialize_calendar(self.config)
        self._add_all_folders()
        self.config.calendar()
        self.config.finalize()
        self._initialize_components()
        self.add_submission_info()
        self.init_coupler()

    def __call__(self):
        if self.config["general"]["jobtype"] == "compute": 
            self.compute()
        elif self.config["general"]["jobtype"] == "tidy_and_resubmit":
            self.tidy()


    def compute(self):
        # make folders
        self._create_folders(self.config["general"], self.all_filetypes)
        self._create_component_folders()
        # write config
        self._write_finalized_config()
        self.copy_tools_to_thisrun()
        # copy date_file etc. into experiment
        self._copy_preliminary_files_from_experiment_to_thisrun()
        # little bit of output
        self._show_simulation_info()
        # assemble file lists and copy everything to thisrun
        self.prepare()
        # write sad file
        self.write_simple_runscript()
        if self.config["general"]["check"]:
            self.end_it_all()
        self.submit()
        self.end_it_all()


    def end_it_all(self):
        if self.config["general"]["profile"]:
            for line in timing_info:
                print(line)       
        sys.exit()


    def tidy(self):
        with open(self.config["general"]["thisrun_scripts_dir"] + "/monitoring_file.out", "w", buffering = 1) as monitor_file:
            monitor_file.write("tidy job initialized \n")
            monitor_file.write("attaching to process " + str(self.config["general"]["launcher_pid"]) + " \n")
            #monitoring_events=self.assemble_monitoring_events()

            filetypes=["log", "mon", "outdata", "restart_out"]
            all_files_to_copy=self.assemble_file_lists(filetypes)
            if self.config["general"]["submitted"]:
                self.wait_and_observe(monitor_file)
            monitor_file.write("job ended, starting to tidy up now \n")
            self.copy_files_from_work_to_thisrun(all_files_to_copy)
            all_listed_filetypes=["log", "mon", "outdata", "restart_out","bin", "config", "forcing", "input", "restart_in"]
            all_files_to_check = self.assemble_file_lists(all_listed_filetypes)
            self.check_for_unknown_files(all_files_to_check)

            monitor_file.write("writing date file \n")
            monitor_file.write("resubmitting \n")
            self.end_it_all()
            self._write_date_file()
            command_line_config["jobtype"] = "compute"
            new_sim = SimulationSetup(command_line_config)
            self.end_it_all()

            

    def prepare(self):
        filetypes=["bin", "config", "forcing", "input", "restart_in"]
        all_files_to_copy = self.assemble_file_lists(filetypes)
        self.copy_files_to_thisrun(all_files_to_copy)
        self.modify_namelists()
        self.modify_files()  # ??? Doing nothing yet
        self.create_new_files(all_files_to_copy)
        self.prepare_coupler_files(all_files_to_copy)
        self.add_batch_hostfile(all_files_to_copy)
        self.copy_files_to_work(all_files_to_copy)





    #####################################    JOB PHASES   ####################################


    ##########################    ASSEMBLE ALL THE INFORMATION  ##############################


    #def assemble_monitoring_events(self):
    #    events={}
    #    events[][



    def check_for_unknown_files(self, listed_files):
        files = os.listdir(self.config["general"]["thisrun_work_dir"])
        unknown_files = []
        for thisfile in files:
            found = False
            file_in_list = False
            file_in_work = False
            if os.path.isfile(self.config["general"]["thisrun_work_dir"] + "/" + thisfile):
                for (file_source, file_intermediate, file_target) in listed_files:
                    #print (file_target.split("/", -1)[-1] + "    " + thisfile)
                    if file_target.split("/", -1)[-1] == thisfile:
                        file_in_list = True
                        if os.path.isfile(file_intermediate):
                            found = True
                            file_in_work = True
                        break
                if not found:
                    unknown_files.append(thisfile)
                if not file_in_list:
                    print ("File is not in list: " + thisfile )
                elif not file_in_work:
                    print ("File is not where it should be: ", thisfile)

#        for thisfile in unknown_files:


    @timing
    def copy_tools_to_thisrun(self):
        gconfig = self.config["general"]

        fromdir = os.path.normpath(gconfig["started_from"])
        scriptsdir = os.path.normpath(gconfig["experiment_scripts_dir"])
        tools_dir = scriptsdir + "/esm_tools/functions"

        print ("Started from :", fromdir)
        print ("Scripts Dir : ", scriptsdir)

        print (fromdir == scriptsdir)
        print (gconfig["update"])

        if os.path.isdir(tools_dir) and gconfig["update"]:
            shutil.rmtree(tools_dir, ignore_errors=True)

        if not os.path.isdir(tools_dir):
            shutil.copytree(gconfig["esm_master_dir"] + "/functions", tools_dir) 

        if (fromdir == scriptsdir) and not gconfig["update"]:
            print ("Started from the experiment folder, continuing...")
        else:
            if not fromdir == scriptsdir:
                print ("Not started from experiment folder, restarting...")
            else:
                print ("Tools were updated, restarting...")

            if not os.path.isfile(scriptsdir + "/" + gconfig["scriptname"]):
                oldscript = fromdir + "/" + gconfig["scriptname"]
                print (oldscript)
                shutil.copy2 (oldscript, scriptsdir)

            for tfile in gconfig["additional_files"]:
                if not os.path.isfile(scriptsdir + "/" + tfile):
                     shutil.copy2 (fromdir + "/" + tfile, scriptsdir)

            restart_command = ("cd " + scriptsdir + "; " + \
                               "esm_tools/functions/general_py/esm_runscripts " + \
                               gconfig["original_command"] )
            print (restart_command)
            os.system( restart_command )

            gconfig["profile"] = False
            self.end_it_all()




    def wait_and_observe(self, monitor_file):
        import time
        while self.job_is_still_running():
            monitor_file.write("still running \n")
            time.sleep(10)
                # possibly monitor shit here

    def job_is_still_running(self):
        import psutil
        if psutil.pid_exists(self.config["general"]["launcher_pid"]):
            return True
        return False

    def add_submission_info(self):
        import esm_batch_system       
        bs = esm_batch_system.esm_batch_system(self.config, self.config["computer"]["batch_system"])

        submitted = bs.check_if_submitted()
        if submitted:
            jobid = bs.get_jobid()
        else:
            jobid = os.getpid()

        self.config["general"]["submitted"] = submitted
        self.config["general"]["jobid"] = jobid


    def _add_all_folders(self):
        self.all_filetypes = ["analysis", "config", "log", "mon", "scripts"]
        self.all_filetypes.append("work")
        for filetype in self.all_filetypes:
            self.config["general"][
                "experiment_" + filetype + "_dir"
            ] = self.config["general"]["base_dir"] + "/" + self.config["general"]["expid"] + "/" + filetype + "/"

        for filetype in self.all_filetypes:
            self.config["general"][
                "thisrun_" + filetype + "_dir"
            ] = self.config["general"]["base_dir"] + "/" + self.config["general"]["expid"] + "/run_" + self.run_datestamp + "/" + filetype + "/"

        self.config["general"]["work_dir"] =  self.config["general"]["thisrun_work_dir"] 

        self.all_model_filetypes = [
            "analysis",
            "bin",
            "config",
            "couple",
            "forcing",
            "input",
            "log",
            "mon",
            "outdata",
            "restart_in",
            "restart_out",
            "viz",
        ]
        for model in self.config["general"]["valid_model_names"]:
             for filetype in self.all_model_filetypes:
                if "restart" in filetype:
                    filedir = "restart"
                else:
                    filedir = filetype
                self.config[model][
                    "experiment_" + filetype + "_dir"
                ] = self.config["general"]["base_dir"] + "/" + self.config["general"]["expid"] + "/" + filedir + "/" + model + "/" 
                self.config[model][ "thisrun_" + filetype + "_dir"
                ] = self.config["general"]["base_dir"] + "/" + self.config["general"]["expid"] + "/run_" + self.run_datestamp + "/" + filedir  + "/" + model + "/" 
                self.config[model]["all_filetypes"] = self.all_model_filetypes

    @timing
    def _read_date_file(self, config, date_file=None):
        if not date_file:
            date_file = (
                config["general"]["base_dir"]
                + "/"
                + config["general"]["expid"]
                + "/scripts/"
                + config["general"]["expid"]
                + "_"
                + config["general"]["setup_name"]
                + ".date"
            )
        if os.path.isfile(date_file):
            logging.info("Date file read from %s", date_file)
            with open(date_file) as date_file:
                date, self.run_number = date_file.readline().strip().split()
            write_file = False
        else:
            logging.info("No date file found %s", date_file)
            logging.info("Initializing run_number=1 and date=18500101")
            date = config["general"].get("initial_date", "18500101")
            self.run_number = 1
            write_file = True
        config["general"]["run_number"] = self.run_number
        self.current_date = Date(date)

        # needs to happen AFTER a run!
        # if write_file:
        #    self._write_date_file()

        logging.info("current_date = %s", self.current_date)
        logging.info("run_number = %s", self.run_number)

    #########################       PREPARE EXPERIMENT / WORK    #############################

    def write_simple_runscript(self):
        sadfilename = self.get_sad_filename()
        header = self.get_batch_header()
        environment = self.get_environment()
        commands = self.get_run_commands()
        tidy_call = "esm_tools/functions/general_py/esm_runscripts " + self.config["general"]["scriptname"] + " -e " + self.config["general"]["expid"] + " -t tidy_and_resubmit -p ${process}"

        with open(sadfilename, "w") as sadfile:
            for line in header:
                sadfile.write(line + "\n")
            sadfile.write("\n")
            for line in environment:
                sadfile.write(line + "\n")
            sadfile.write("\n")
            sadfile.write("cd "+ self.config["general"]["thisrun_work_dir"] + "\n")
            for line in commands: 
                sadfile.write(line + "\n")
            sadfile.write("process=$! \n")
            sadfile.write("cd "+ self.config["general"]["thisrun_scripts_dir"] + "\n")
            sadfile.write(tidy_call + "\n")

        self.submit_command = self.get_submit_command(sadfilename)

        six.print_("\n", 40 * "+ ")
        six.print_("Contents of ",sadfilename, ":")
        with open(sadfilename, "r") as fin:
            print (fin.read())
        six.print_("\n", 40 * "+ ")
        six.print_("Contents of ",self.batch.bs.filename, ":")
        with open(self.batch.bs.path, "r") as fin:
            print (fin.read())
    
    def get_sad_filename(self):
        folder = self.config["general"]["thisrun_scripts_dir"]
        expid = self.config["general"]["expid"]
        startdate = self.config["general"]["current_date"]
        enddate = self.config["general"]["end_date"]
        return folder + "/" + expid+"_"+self.run_datestamp+".sad"

    def get_batch_header(self):
        header = []
        batch_system = self.config["computer"]
        if "sh_interpreter" in batch_system:
            header.append("#!"+batch_system["sh_interpreter"])
        tasks = self.calculate_requirements()
        replacement_tags = [("@tasks@", tasks)]
        all_flags = ["partition_flag",
                     "time_flag",
                     "tasks_flag",
                     "output_flags",
                     "name_flag",
                    ]
        conditional_flags = ["accounting_flag",
                             "notification_flag",
                             "hyperthreading_flag",
                             "additional_flags"
                            ]
        if self.config["general"]["jobtype"] in ["compute", "tidy_and_resume"]:
            conditional_flags.append("exclusive_flag")
        for flag in conditional_flags:
            if flag in batch_system and not batch_system[flag].strip() == "":
                all_flags.append(flag)
        for flag in all_flags:
            for (tag, repl) in replacement_tags:
                batch_system[flag] = batch_system[flag].replace(tag, str(repl))
            header.append(batch_system["header_start"] + " " + batch_system[flag])
        return header
    
    def calculate_requirements(self):
        tasks = 0
        for model in self.config["general"]["models"]:
            if "nproc" in self.config[model]:
                tasks += self.config[model]["nproc"]
            elif "nproca" in self.config[model] and "nprocb" in self.config[model]:
                tasks += self.config[model]["nproca"] * self.config[model]["nprocb"]
        return tasks

    def get_environment(self):
        environment = []
        import esm_environment
        env = esm_environment.environment_infos()
        if "module_actions" in env.config:
            for action in env.config["module_actions"]:
                environment.append("module " + action)
        environment.append("")
        if "export_vars" in env.config:
            for var in env.config["export_vars"].keys():
                environment.append(
                    "export " + var + "=" + env.config["export_vars"][var]
                )
        for model in self.config:
            if not model == "computer":
                if "module_actions" in self.config[model]:
                    for action in self.config[model]["module_actions"]:
                        environment.append("module " + action)
                environment.append("")
                if "export_vars" in self.config[model]:
                    for var in self.config[model]["export_vars"].keys():
                        if type(self.config[model]["export_vars"][var]) == dict:
                            sys.stdout = mystdout = StringIO()
                            esm_parser.pprint_config(self.config[model]["export_vars"][var])
                            sys.stdout = sys.__stdout__
                            exportvar = mystdout.getvalue()
                            environment.append(
                                "export " + var + "=$(cat << EOF"
                            )
                            environment.append(exportvar)
                            environment.append("EOF")
                            environment.append(")")
                        else:
                            environment.append(
                                "export " + var + "=" + str(self.config[model]["export_vars"][var])
                            )
        return environment

    def get_run_commands(self):
        commands = []
        batch_system = self.config["computer"]
        if "execution_command" in batch_system:
            commands.append(batch_system["execution_command"] + " &")
        return commands

    def get_submit_command(self, sadfilename):
        commands = []
        batch_system = self.config["computer"]
        if "submit" in batch_system:
            commands.append("cd " + self.config["general"]["thisrun_scripts_dir"] + "; " + batch_system["submit"] + " " +sadfilename)
        return commands








    def submit(self):
        six.print_("\n", 40 * "+ ")
        print ("Submitting sad jobscript to batch system...")
        for command in self.submit_command:
            print (command)
        six.print_("\n", 40 * "+ ")
        for command in self.submit_command:
            os.system(command)
        sys.exit()




    #########################################################################################

    def _initialize_components(self):
        components = []
        for component in self.config["general"]["valid_model_names"]:
            components.append(
                SimulationComponent(self.config["general"], self.config[component])
            )
        self.components = components

    def _create_folders(self, config, filetypes):
        for filetype in filetypes:
            if not os.path.exists(config["experiment_" + filetype + "_dir"]):
                os.makedirs(config["experiment_" + filetype + "_dir"])
            if not os.path.exists(config["thisrun_" + filetype + "_dir"]):
                os.makedirs(config["thisrun_" + filetype + "_dir"])

    def _dump_final_yaml(self):
        with open(
            self.experiment_config_dir
            + "/"
            + self.config["general"]["expid"]
            + "_preconfig.yaml",
            "w",
        ) as config_file:
            yaml.dump(self.config, config_file)

    def _show_simulation_info(self):
        six.print_(80 * "=")
        six.print_("STARTING SIMULATION JOB!")
        six.print_("Experiment ID = %s" % self.config["general"]["expid"])
        six.print_("Setup = %s" % self.config["general"]["setup_name"])
        six.print_("This setup consists of:")
        for model in self.config["general"]["valid_model_names"]:
            six.print_("- %s" % model)
        six.print_("You are using the Python version.")


    def _write_finalized_config(self):
        #pp.pprint(self.config)
        with open(
            self.config["general"]["thisrun_config_dir"]
            + "/"
            + self.config["general"]["expid"]
            + "_finished_config.yaml",
            "w",
        ) as config_file:
            yaml.dump(self.config, config_file)

    def _create_component_folders(self):
        for component in self.components:
            #component.general_config = self.config["general"]
            self._create_folders(component.config, self.all_model_filetypes)

    def _copy_preliminary_files_from_experiment_to_thisrun(self):
        filelist = [
            (
                "scripts",
                self.config["general"]["expid"]
                + "_"
                + self.config["general"]["setup_name"]
                + ".date",
                "copy",
            )
        ]
        for filetype, filename, copy_or_link in filelist:
            source = self.config["general"]["experiment_" + filetype + "_dir"]
            dest = self.config["general"]["thisrun_" + filetype + "_dir"]
            if copy_or_link == "copy":
                method = shutil.copy2
            elif copy_or_link == "link":
                method = os.symlink
            if os.path.isfile(source + "/" + filename):
                method(source + "/" + filename, dest + "/" + filename)
        this_script = self.config["general"]["scriptname"]
        shutil.copy2("./" + this_script, self.config["general"]["thisrun_scripts_dir"])

        for additional_file in self.config["general"]["additional_files"]:
            shutil.copy2(additional_file, self.config["general"]["thisrun_scripts_dir"])


    def _initialize_calendar(self, config):
        nyear, nmonth, nday, nhour, nminute, nsecond = 0, 0, 0, 0, 0, 0
        nyear = int(config["general"].get("nyear", nyear))
        if not nyear:
            nmonth = int(config["general"].get("nmonth", nmonth))
        if not nyear and not nmonth:
            nday = int(config["general"].get("nday", nday))
        if not nyear and not nmonth and not nday:
            nhour = int(config["general"].get("nhour", nhour))
        if not nyear and not nmonth and not nday and not nhour:
            nminute = int(config["general"].get("nminute", nminute))
        if not nyear and not nmonth and not nday and not nhour and not nminute:
            nsecond = int(config["general"].get("nsecond", nsecond))
        if (
            not nyear
            and not nmonth
            and not nday
            and not nhour
            and not nminute
            and not nsecond
        ):
            nyear = 1

        self.delta_date = (nyear, nmonth, nday, nhour, nminute, nsecond)
        config["general"]["current_date"] = self.current_date
        config["general"]["start_date"] = self.current_date
        config["general"]["initial_date"] = Date(config["general"]["initial_date"])
        config["general"]["final_date"] = Date(config["general"]["final_date"])
        #config["general"]["prev_date"] = self.current_date.sub((0, 0, 1, 0, 0, 0))
        config["general"]["prev_date"] = self.current_date - (0, 0, 1, 0, 0, 0)

        config["general"]["next_date"] = self.current_date.add(self.delta_date)
        #config["general"]["end_date"] = config["general"]["next_date"].sub(
        config["general"]["end_date"] = config["general"]["next_date"] - (0, 0, 1, 0, 0, 0)
    
        config["general"]["runtime"] = (
            config["general"]["next_date"] - config["general"]["current_date"]
        )

        config["general"]["total_runtime"] = (
            config["general"]["next_date"] - config["general"]["initial_date"]
        )

        self.run_datestamp = (
            config["general"]["current_date"].format(
                form=9, givenph=False, givenpm=False, givenps=False
            )
            + "-"
            + config["general"]["end_date"].format(
                form=9, givenph=False, givenpm=False, givenps=False
            )
        )

    def _increment_date_and_run_number(self):
        self.run_number += 1
        self.current_date += self.delta_date

    def _write_date_file(self, date_file=None):
        if not date_file:
            date_file = (
                self.experiment_scripts_dir
                + "/"
                + self.config["general"]["expid"]
                + "_"
                + self.config["general"]["setup_name"]
                + ".date"
            )
        with open(date_file, "w") as date_file:
            date_file.write(self.current_date.output() + " " + str(self.run_number))


    def assemble_file_lists(self, filetypes):
        all_files_to_copy = []
        six.print_("\n" "- Generating file lists for this run...")
        for component in self.components:
            six.print_("-" * 80)
            six.print_("* %s" % component.config["model"], "\n")
            all_component_files, filetype_specific_dict = (
                component.filesystem_to_experiment(filetypes)
            )
            with open(
                component.config["thisrun_config_dir"]
                + "/"
                + self.config["general"]["expid"]
                + "_filelist_"
                + self.run_datestamp,
                "w",
            ) as flist:
                flist.write(
                    "These files are used for \nexperiment %s\ncomponent %s\ndate %s"
                    % (
                        self.config["general"]["expid"],
                        component.config["model"],
                        self.run_datestamp,
                    )
                )
                flist.write("\n")
                flist.write(80 * "-")
                for filetype in filetype_specific_dict:
                    flist.write("\n" + filetype.upper() + ":\n")
                    for source, exp_tree_name, work_dir_name in filetype_specific_dict[
                        filetype
                    ]:
                        flist.write("\nSource: " + source)
                        flist.write("\nExp Tree: " + exp_tree_name)
                        flist.write("\nWork Dir: " + work_dir_name)
                        flist.write("\n")
                    flist.write("\n")
                    flist.write(80 * "-")
            esm_parser.pprint_config(filetype_specific_dict)
            all_files_to_copy += all_component_files
        return all_files_to_copy


    def copy_files_to_thisrun(self, all_files_to_copy):
        six.print_("=" * 80, "\n")
        six.print_("PREPARING EXPERIMENT")
        # Copy files:
        six.print_("\n" "- File lists populated, proceeding with copy...")
        six.print_("- Note that you can see your file lists in the config folder")
        six.print_("- You will be informed about missing files")
        successful_files = []
        missing_files = []
        # TODO: Check if we are on login node or elsewhere for the progress
        # bar, it doesn't make sense on the compute nodes:
        flist = all_files_to_copy
        for ftuple in tqdm.tqdm(
            flist,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ):
            logging.debug(ftuple)
            (file_source, file_intermediate, file_target) = ftuple
            try:
                shutil.copy2(file_source, file_intermediate)
                if not os.path.isfile(file_target):
                    os.symlink(file_intermediate, file_target)
                successful_files.append(file_target)
            except IOError:
                missing_files.append(file_target)
        if missing_files:
            six.print_("--- WARNING: These files were missing:")
            for missing_file in missing_files:
                six.print_("- %s" % missing_file)


    def copy_files_from_work_to_thisrun(self, all_files_to_copy):
        six.print_("=" * 80, "\n")
        six.print_("COPYING STUFF FROM WORK TO THISRUN FOLDERS")
        # Copy files:
        successful_files = []
        missing_files = []
        # TODO: Check if we are on login node or elsewhere for the progress
        # bar, it doesn't make sense on the compute nodes:
        flist = all_files_to_copy
        for ftuple in tqdm.tqdm(
            flist,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ):
            logging.debug(ftuple)
            (file_source, file_intermediate, file_target) = ftuple
            file_source = self.config["general"]["thisrun_work_dir"] + "/" + file_target.split("/", -1)[-1]
            try:
                shutil.copy2(file_source, file_intermediate)
                if not os.path.isfile(file_target):
                    os.symlink(file_intermediate, file_target)
                successful_files.append(file_target)
            except IOError:
                missing_files.append(file_target)
        if missing_files:
            six.print_("--- WARNING: These files were missing:")
            for missing_file in missing_files:
                six.print_("- %s" % missing_file)

    def modify_namelists(self):
        # Load and modify namelists:
        six.print_("\n" "- Setting up namelists for this run...")
        all_namelists = {}
        for component in self.components:
            six.print_("-" * 80)
            six.print_("* %s" % component.config["model"], "\n")
            component.nmls_load()
            component.nmls_remove()
            component.nmls_modify()
            component.nmls_finalize(all_namelists)
        six.print_(
            "\n" "- Namelists modified according to experiment specifications..."
        )
        for nml_name, nml in all_namelists.items():
            six.print_("Contents of ", nml_name, ":")
            nml.write(sys.stdout)
            six.print_("\n", 40 * "+ ")


    def modify_files(self):
        for model in self.config['general']['valid_model_names']:
            for filetype in self.all_model_filetypes: 
                #print(self.config[model].get(filetype+"_modifications"))
                if filetype == "restart":
                    nothing = "nothing"
                    #print(self.config[model].get(filetype+"_in_modifications"))


    def create_new_files(self, all_files_to_copy):
        for model in list(self.config):
            for filetype in self.all_filetypes:
                if "create_"+filetype in self.config[model]:
                    filenames = self.config[model]["create_"+filetype].keys()
                    for filename in filenames:
                        with open(self.config["general"]["thisrun_" + filetype + "_dir"] + "/" +filename, "w") as createfile:
                            actionlist = self.config[model]["create_"+filetype][filename]
                            for action in actionlist:
                                if "<--append--" in action:
                                    appendtext = action.replace("<--append--", "")
                                    createfile.write(appendtext.strip() + "\n")
                        all_files_to_copy.append(
                            (
                                "",
                                "",
                                self.config["general"]["thisrun_" + filetype + "_dir"] + "/" +filename,
                            )
                        )


    def init_coupler(self):
        for model in list(self.config):
            if model in esm_coupler.known_couplers:
                self.coupler_config_dir = (
                    self.config["general"]["base_dir"]
                    + "/"
                    + self.config["general"]["expid"]
                    + "/run_"
                    + self.run_datestamp
                    + "/config/"
                    + model
                    + "/"
                )
                self.coupler = esm_coupler.esm_coupler(self.config, model)
                break
        self.coupler.add_output_files(self.config)   

    def prepare_coupler_files(self, all_files_to_copy):
        self.coupler.prepare(self.config, self.coupler_config_dir)
        coupler_filename="namcouple"  # needs to be set by function above
        all_files_to_copy.append(
            (
                "",
                "",
                self.coupler_config_dir + "/" + coupler_filename,
            )
        )
        #print (coupler_config_dir + "/" + coupler_filename)



    def add_batch_hostfile(self, all_files_to_copy):
        import esm_batch_system
        self.batch = esm_batch_system.esm_batch_system(self.config, self.config["computer"]["batch_system"])
        self.batch.calc_requirements(self.config)

        all_files_to_copy.append(
            (
                "",
                "",
                self.batch.bs.path,
            )
        )



    def copy_files_to_work(self, flist):
        successful_files = []
        missing_files = []
        # TODO: Check if we are on login node or elsewhere for the progress
        # bar, it doesn't make sense on the compute nodes:
        for ftuple in tqdm.tqdm(
            flist,
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ):
            logging.debug(ftuple)
            (file_source, file_intermediate, file_target) = ftuple
            file_in_work = self.config["general"]["thisrun_work_dir"] + "/" + file_target.split("/", -1)[-1]
            try:
                shutil.copy2(file_target, file_in_work)
                successful_files.append(file_target)
            except IOError:
                missing_files.append(file_target)
        if missing_files:
            six.print_("--- WARNING: These files were missing:")
            for missing_file in missing_files:
                six.print_("- %s" % missing_file)
        #sys.exit()








    ################################# COMPONENT ###########################################



class SimulationComponent(object):
    def __init__(self, general, component_config):
        self.config = component_config
        self.general_config = general

    def find_correct_source(self, file_source, year):
        if isinstance(file_source, dict):
            logging.debug(
                "Checking which file to use for this year: %s",
                year,
            )
            for fname, valid_years in six.iteritems(file_source):
                logging.debug("Checking %s", fname)
                min_year = float(valid_years.get("from", "-inf"))
                max_year = float(valid_years.get("to", "inf"))
                logging.debug("Valid from: %s", min_year)
                logging.debug("Valid to: %s", max_year)
                logging.debug(
                    "%s <= %s --> %s",
                    min_year,
                    year,
                    min_year <= year,
                )
                logging.debug(
                    "%s <= %s --> %s",
                    year,
                    max_year,
                    year <= max_year,
                )
                if (
                    min_year <= year
                    and year <= max_year
                ):
                    return fname
                else:
                    continue
        return file_source



    def filesystem_to_experiment(self, filetypes):
        all_files_to_process = []
        filetype_files_for_list = {}
        for filetype in filetypes:
        #for filetype in self.config["all_filetypes"]:
            filetype_files = []
            six.print_("- %s" % filetype)
            if filetype == "restart_in" and not self.config["lresume"]:
                six.print_("- restart files do not make sense for a cold start, skipping...")
                continue
            if filetype + "_sources" not in self.config:
                continue
            filedir_intermediate = self.config["thisrun_" + filetype + "_dir"]
            for file_descriptor, file_source in six.iteritems(
                self.config[filetype + "_sources"]
            ):
                logging.debug(
                    "file_descriptor=%s, file_source=%s", file_descriptor, file_source
                )
                if filetype + "_files" in self.config:
                    if file_descriptor not in self.config[filetype + "_files"].values():
                        continue
                    else:
                        inverted_dict = {}
                        for k, v in six.iteritems(self.config[filetype + "_files"]):
                            inverted_dict[v] = k
                        file_category = inverted_dict[file_descriptor]
                else:
                    file_category = file_descriptor

                logging.debug(type(file_source))

                # should be generalized to all sorts of dates on day

                all_years = [self.general_config["current_date"].year]
                if (
                   filetype + "_additional_information" in self.config
                   and file_category in self.config[filetype + "_additional_information"]
                ):
                    if (
                       "need_timestep_before" in self.config[filetype + "_additional_information"][file_category]
                    ):
                        all_years.append(self.general_config["prev_date"].year)
                    if (
                       "need_timestep_after" in self.config[filetype + "_additional_information"][file_category]
                    ):
                        all_years.append(self.general_config["next_date"].year)
                    if (
                       "need_year_before" in self.config[filetype + "_additional_information"][file_category]
                    ):
                        all_years.append(self.general_config["current_date"].year - 1)
                    if (
                       "need_year_after" in self.config[filetype + "_additional_information"][file_category]
                    ):
                        all_years.append(self.general_config["next_date"].year + 1 )

                all_years = list(dict.fromkeys(all_years)) # removes duplicates

                if (
                    filetype + "_in_work" in self.config
                    and file_category in self.config[filetype + "_in_work"].keys()
                ):
                    target_name = self.config[filetype + "_in_work"][file_category]
                else:
                    target_name = os.path.basename(file_source)

                for year in all_years:

                    this_target_name=target_name.replace("@YEAR@", str(year))
                    source_name=self.find_correct_source(file_source, year)
                    file_target = (
                        filedir_intermediate + "/" + this_target_name
                    )

                    filetype_files.append(
                        (
                            source_name,
                            filedir_intermediate + "/" + os.path.basename(source_name),
                            file_target,
                        )
                    )

            filetype_files_for_list[filetype] = filetype_files
            all_files_to_process += filetype_files
        return all_files_to_process, filetype_files_for_list

    def nmls_load(self):
        nmls = self.config.get("namelists", [])
        self.config["namelists"] = dict.fromkeys(nmls)
        for nml in nmls:
            logging.debug("Loading %s", nml)
            self.config["namelists"][nml] = f90nml.read(
                os.path.join(self.config["thisrun_config_dir"], nml)
            )

    def nmls_remove(self):
        namelist_changes = self.config.get("namelist_changes", {})
        namelist_removes = []
        for namelist in list(namelist_changes):
            changes = namelist_changes[namelist]
            logging.debug("Determining remove entires for %s", namelist)
            logging.debug("All changes: %s", changes)
            for change_chapter in list(changes):
                change_entries = changes[change_chapter]
                for key in list(change_entries):
                    value = change_entries[key]
                    if value == "remove_from_namelist":
                        namelist_removes.append((namelist, change_chapter, key))
                        del namelist_changes[namelist][change_chapter][key]
        for remove in namelist_removes:
            namelist, change_chapter, key = remove
            logging.debug("Removing from %s: %s, %s", namelist, change_chapter, key)
            if key in self.config["namelists"][namelist][change_chapter]:
                del self.config["namelists"][namelist][change_chapter][key]

    def nmls_modify(self):
        namelist_changes = self.config.get("namelist_changes", {})
        for namelist, changes in six.iteritems(namelist_changes):
            self.config["namelists"][namelist].patch(changes)

    def nmls_finalize(self, all_nmls):
        for nml_name, nml_obj in six.iteritems(self.config.get("namelists", {})):
            with open(os.path.join(self.config["thisrun_config_dir"], nml_name), "w") as nml_file:
                nml_obj.write(nml_file)
            #if nml_name == "namelist.echam":
            #    pp.pprint(nml_obj)
            #    print(80*"*")
            #    pp.pprint(str(nml_obj))
            #    sys.exit(1)
            all_nmls[nml_name] = nml_obj  # PG or a string representation?

