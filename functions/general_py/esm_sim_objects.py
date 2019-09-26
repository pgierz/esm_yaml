"""
Documentation goes here
"""
import logging
import os
import shutil
import sys

import externals
import f90nml
import six
import tqdm
import yaml


from esm_calendar import Date
import esm_parser


def date_representer(dumper, date):
    return dumper.represent_str("%s" % date.output())


yaml.add_representer(Date, date_representer)


class SimulationSetup(object):
    def __init__(self, name, user_config):

        self.config = esm_parser.ConfigSetup(name, user_config)

        self.config["general"]["base_dir"] = self.config["general"]["BASE_DIR"]
        self.config["general"]["expid"] = "test"

        components = []
        for component in self.config["general"]["valid_model_names"]:
            components.append(
                SimulationComponent(self.config["general"], self.config[component])
            )
        del user_config
        self.components = components

        self.all_filetypes = ["analysis", "config", "log", "mon", "scripts"]
        for filetype in self.all_filetypes:
            setattr(
                self,
                "experiment_" + filetype + "_dir",
                self.config["general"]["base_dir"]
                + "/"
                + self.config["general"]["expid"]
                + "/"
                + filetype
                + "/",
            )
            if not os.path.exists(getattr(self, "experiment_" + filetype + "_dir")):
                os.makedirs(getattr(self, "experiment_" + filetype + "_dir"))
        with open(
            self.experiment_config_dir
            + "/"
            + self.config["general"]["expid"]
            + "_preconfig.yaml",
            "w",
        ) as config_file:
            yaml.dump(self.config, config_file)

        self._read_date_file()
        self._initialize_calendar()
        self._finalize_config()
        esm_parser.pprint_config(self.config)
        sys.exit()
        self._finalize_components()
        self._finalize_attributes()
        self._write_finalized_config()
        self._copy_preliminary_files_from_experiment_to_thisrun()
        self._show_simulation_info()

    def _show_simulation_info(self):
        six.print_(80 * "=")
        six.print_("STARTING SIMULATION JOB!")
        six.print_("Experiment ID = %s" % self.config["general"]["expid"])
        six.print_("Setup = %s" % self.config["general"]["setup_name"])
        six.print_("This setup consists of:")
        for model in self.config["general"]["valid_model_names"]:
            six.print_("- %s" % model)
        six.print_("You are using the Python version.")

    def _finalize_config(self):
        # esm_parser.psix.print_config(self.config["hdmodel"])
        logging.debug("SECOND TIME!")
        self.config.choose_blocks(self.config, isblacklist=False)
        self.config.run_recursive_functions(self.config, isblacklist=False)

    def _finalize_attributes(self):
        for filetype in self.all_filetypes:
            setattr(
                self,
                "thisrun_" + filetype + "_dir",
                self.config["general"]["base_dir"]
                + "/"
                + self.config["general"]["expid"]
                + "/run_"
                + self.config["general"]["current_date"].format(
                    form=9, givenph=False, givenpm=False, givenps=False
                )
                + "-"
                + self.config["general"]["end_date"].format(
                    form=9, givenph=False, givenpm=False, givenps=False
                )
                + "/"
                + filetype
                + "/",
            )
            if not os.path.exists(getattr(self, "thisrun_" + filetype + "_dir")):
                os.makedirs(getattr(self, "thisrun_" + filetype + "_dir"))
        self.run_datestamp = (
            self.config["general"]["current_date"].format(
                form=9, givenph=False, givenpm=False, givenps=False
            )
            + "-"
            + self.config["general"]["end_date"].format(
                form=9, givenph=False, givenpm=False, givenps=False
            )
        )

    def _write_finalized_config(self):
        with open(
            self.thisrun_config_dir
            + "/"
            + self.config["general"]["expid"]
            + "_finished_config.yaml",
            "w",
        ) as config_file:
            yaml.dump(self.config, config_file)

    def _finalize_components(self):
        for component in self.components:
            component.general_config = self.config["general"]
            component.finalize_attributes()

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
            source = getattr(self, "experiment_" + filetype + "_dir")
            dest = getattr(self, "thisrun_" + filetype + "_dir")
            if copy_or_link == "copy":
                method = shutil.copy2
            elif copy_or_link == "link":
                method = os.symlink
            method(source + "/" + filename, dest + "/" + filename)

    def _read_date_file(self, date_file=None):
        if not date_file:
            date_file = (
                self.experiment_scripts_dir
                + "/"
                + self.config["general"]["expid"]
                + "_"
                + self.config["general"]["setup_name"]
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
            date = self.config["general"].get("INITIAL_DATE", "18500101")
            self.run_number = 1
            write_file = True
        self.current_date = Date(date)

        if write_file:
            self._write_date_file()

        logging.info("current_date = %s", self.current_date)
        logging.info("run_number = %s", self.run_number)

    def _initialize_calendar(self):
        nyear, nmonth, nday, nhour, nminute, nsecond = 0, 0, 0, 0, 0, 0
        nyear = self.config["general"].get("nyear", nyear)
        if not nyear:
            nmonth = self.config["general"].get("nmonth", nmonth)
        if not nyear and not nmonth:
            nday = self.config["general"].get("nday", nday)
        if not nyear and not nmonth and not nday:
            nhour = self.config["general"].get("nhour", nhour)
        if not nyear and not nmonth and not nday and not nhour:
            nminute = self.config["general"].get("nminute", nminute)
        if not nyear and not nmonth and not nday and not nhour and not nminute:
            nsecond = self.config["general"].get("nsecond", nsecond)
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
        self.config["general"]["current_date"] = self.current_date
        self.config["general"]["initial_date"] = Date(
            self.config["general"]["INITIAL_DATE"]
        )
        self.config["general"]["final_date"] = Date(
            self.config["general"]["FINAL_DATE"]
        )
        self.config["general"]["prev_date"] = self.current_date.sub((0, 0, 1, 0, 0, 0))

        self.config["general"]["next_date"] = self.current_date.add(self.delta_date)
        self.config["general"]["end_date"] = self.config["general"]["next_date"].sub(
            (0, 0, 1, 0, 0, 0)
        )
        self.config["general"]["runtime"] = (
            self.config["general"]["next_date"] - self.config["general"]["current_date"]
        )

        self.config["general"]["total_runtime"] = (
            self.config["general"]["next_date"] - self.config["general"]["initial_date"]
        )

        # Last step: figure out if we are doing a cold start of a restart:
        if self.run_number != 1:
            for component in self.components:
                component.config["lresume"] = True
        else:
            # Did the user give a value? If yes, keep it, if not, first run:
            for component in self.components:
                user_lresume = component.config.get("LRESUME", False)
                component.config.setdefault("lresume", user_lresume)

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

    def prepare(self):
        six.print_("=" * 80, "\n")
        six.print_("PREPARING EXPERIMENT")
        # Copy files:
        all_files_to_copy = []
        six.print_("\n" "- Generating file lists for this run...")
        for component in self.components:
            six.print_("-" * 80)
            six.print_("* %s" % component.config["model"], "\n")
            all_component_files, filetype_specific_dict = (
                component.filesystem_to_experiment()
            )
            with open(
                component.thisrun_config_dir
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
        six.print_("\n" "- File lists populated, proceeding with copy...")
        six.print_("- Note that you can see your file lists in the config folder")
        six.print_("- You will be informed about missing files")
        self._prepare_copy_files(all_files_to_copy)

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

    def _prepare_copy_files(self, flist):
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


class SimulationComponent(object):
    def __init__(self, general, component_config):
        self.config = component_config
        self.general_config = general

        self.all_filetypes = [
            "analysis",
            "bin",
            "config",
            "couple",
            "forcing",
            "input",
            "log",
            "mon",
            "outdata",
            "restart",
            "viz",
        ]

        for filetype in self.all_filetypes:
            setattr(
                self,
                "experiment_" + filetype + "_dir",
                self.general_config["base_dir"]
                + "/"
                + self.general_config["expid"]
                + "/"
                + filetype
                + "/"
                + self.config["model"]
                + "/",
            )
            if not os.path.exists(getattr(self, "experiment_" + filetype + "_dir")):
                os.makedirs(getattr(self, "experiment_" + filetype + "_dir"))

    def filesystem_to_experiment(self):
        all_files_to_process = []
        filetype_files_for_list = {}
        for filetype in self.all_filetypes:
            filetype_files = []
            six.print_("- %s" % filetype)
            if filetype + "_sources" not in self.config:
                continue
            filedir_intermediate = getattr(self, "thisrun_" + filetype + "_dir")
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
                if isinstance(file_source, dict):
                    logging.debug(
                        "Checking which file to use for this year: %s",
                        self.general_config["current_date"].year,
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
                            self.general_config["current_date"].year,
                            min_year <= self.general_config["current_date"].year,
                        )
                        logging.debug(
                            "%s <= %s --> %s",
                            self.general_config["current_date"].year,
                            max_year,
                            self.general_config["current_date"].year <= max_year,
                        )
                        if (
                            min_year <= self.general_config["current_date"].year
                            and self.general_config["current_date"].year <= max_year
                        ):
                            file_source = fname
                        else:
                            continue
                if (
                    filetype + "_in_work" in self.config
                    and file_category in self.config[filetype + "_in_work"].keys()
                ):
                    file_target = (
                        filedir_intermediate
                        + "/"
                        + self.config[filetype + "_in_work"][file_category]
                    )
                else:
                    if isinstance(file_source, str):
                        file_target = (
                            filedir_intermediate + "/" + os.path.basename(file_source)
                        )
                    else:
                        raise TypeError(
                            "Don't know what to do, sorry. You gave %s" % file_source
                        )
                logging.debug(file_source)
                filetype_files.append(
                    (
                        file_source,
                        filedir_intermediate + "/" + os.path.basename(file_source),
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
                os.path.join(self.thisrun_config_dir, nml)
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
            del self.config["namelists"][namelist][change_chapter][key]

    def nmls_modify(self):
        namelist_changes = self.config.get("namelist_changes", {})
        for namelist, changes in six.iteritems(namelist_changes):
            self.config["namelists"][namelist].patch(changes)

    def nmls_finalize(self, all_nmls):
        for nml_name, nml_obj in six.iteritems(self.config.get("namelists", {})):
            with open(os.path.join(self.thisrun_config_dir, nml_name), "w") as nml_file:
                nml_obj.write(nml_file)
            all_nmls[nml_name] = nml_obj  # PG or a string representation?

    def finalize_attributes(self):
        for filetype in self.all_filetypes:
            setattr(
                self,
                "thisrun_" + filetype + "_dir",
                self.general_config["base_dir"]
                + "/"
                + self.general_config["expid"]
                + "/run_"
                + self.general_config["current_date"].format(
                    form=9, givenph=False, givenpm=False, givenps=False
                )
                + "-"
                + self.general_config["end_date"].format(
                    form=9, givenph=False, givenpm=False, givenps=False
                )
                + "/"
                + filetype
                + "/"
                + self.config["model"]
                + "/",
            )
            if not os.path.exists(getattr(self, "thisrun_" + filetype + "_dir")):
                os.makedirs(getattr(self, "thisrun_" + filetype + "_dir"))
