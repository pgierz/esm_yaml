"""
Documentation goes here
"""
import os
import shutil

from esm_calendar import Date
import logging
import tqdm
import yaml

import esm_parser


def date_representer(dumper, date):
    return dumper.represent_str(u"%s" % date.output())


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
        self._finalize_components()

    def _finalize_config(self):
        # esm_parser.pprint_config(self.config["hdmodel"])
        logging.debug("SECOND TIME!")
        self.config.choose_blocks(self.config, isblacklist=False)
        self.config.run_recursive_functions(self.config, isblacklist=False)
        with open(
            self.experiment_config_dir
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
        print("=" * 80, "\n")
        print("PREPARING EXPERIMENT")
        # Copy files:
        all_files_to_copy = []
        for component in self.components:
            print("-" * 80)
            print("* %s" % component.config["model"], "\n")
            all_files_to_copy += component.filesystem_to_experiment()
        print("\n" "- File lists populated, proceeding with copy...")
        self._prepare_copy_files(all_files_to_copy)

        # Load and modify namelists:
        all_namelists = {}
        for component in self.components:
            print("-" * 80)
            print("* %s" % component.config["model"], "\n")
            component.nmls_load()
            component.nmls_remove()
            component.nmls_modify()
            component.nmls_finalize(all_namelists)
        print("\n" "- Namelists modified according to experiment specifications")
        for nml_name, nml in all_namelists.items():
            print("Contents of ", nml_name, ":")
            print(nml)

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
            print("--- WARNING: These files were missing:")
            for missing_file in missing_files:
                print("- %s" % missing_file)


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
        print("- Gathering files to be copied to experiment tree:")
        all_files_to_process = []
        for filetype in self.all_filetypes:
            filetype_files = []
            print("- %s" % filetype)
            if filetype + "_sources" not in self.config:
                continue
            filedir_intermediate = getattr(self, "thisrun_" + filetype + "_dir")
            for file_descriptor, file_source in self.config[
                filetype + "_sources"
            ].items():
                logging.debug(
                    "file_descriptor=%s, file_source=%s", file_descriptor, file_source
                )
                if filetype + "_files" in self.config:
                    if file_descriptor not in self.config[filetype + "_files"].values():
                        continue
                    else:
                        inverted_dict = {
                            v: k for k, v in self.config[filetype + "_files"].items()
                        }
                        file_category = inverted_dict[file_descriptor]
                else:
                    file_category = file_descriptor

                logging.debug(type(file_source))
                if isinstance(file_source, dict):
                    logging.debug(
                        "Checking which file to use for this year: %s",
                        self.general_config["current_date"].year,
                    )
                    for fname, valid_years in file_source.items():
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
                            continue  # PG: With the big loop?
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
            all_files_to_process += filetype_files
        return all_files_to_process

    def nmls_load(self):
        nmls = self.config.get("namelists")
        self.config["namelists"] = dict.fromkeys(nmls)
        for nml in nmls:
            self.config["namelists"][nml] = f90nml.read(
                os.path.join(self.config_dir, nml)
            )

    def nmls_remove(self):
        namelist_changes = self.config.get("namelist_changes", {})
        namelist_removes = []
        for namelist, changes in namelist_changes.items():
            for change_chapter, change_entries in changes:
                for key, value in change_entries:
                    if value == "remove_from_namelist":
                        namelist_removes.append((namelist, change_chapter, key))
                        del namelist_changes[namelist][change_chapter][key]
        for remove in namelist_removes:
            namelist, change_chapter, key = remove
            del self.config["namelists"][namelist][change_chapter][key]

    def nmls_modify(self):
        namelist_changes = self.config.get("namelist_changes", {})
        for namelist, changes in namelist_changes.items():
            self.config["namelists"][namelist].patch(changes)

    def nmls_finalize(self, all_nmls):
        for nml_name, nml_obj in self.config.get("namelists", {}).items():
            with open(os.path.join(self.config_dir, nml_name), "w") as nml_file:
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
                + self.general_config["current_date"].output()
                + "-"
                + self.general_config["end_date"].output()
                + "/"
                + filetype
                + "/"
                + self.config["model"]
                + "/",
            )
            if not os.path.exists(getattr(self, "thisrun_" + filetype + "_dir")):
                os.makedirs(getattr(self, "thisrun_" + filetype + "_dir"))
