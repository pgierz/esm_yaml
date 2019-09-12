"""
Documentation goes here
"""
import os
import shutil

from esm_calendar import Date
import logging
import yaml

import esm_parser


def date_representer(dumper, date):
    return dumper.represent_str(u"%s" % date.output())


yaml.add_representer(Date, date_representer)


class SimulationSetup(object):
    def __init__(self, name, user_config):

        self.config = esm_parser.ConfigSetup(name, user_config)

        self.config["general"]["base_dir"] = "/tmp/example_experiments/"
        self.config["general"]["expid"] = "test"

        components = []
        for component in self.config["general"]["valid_model_names"]:
            components.append(
                SimulationComponent(self.config["general"], self.config[component])
            )
        del user_config
        # Maybe this wastes memory, not sure:
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
        # esm_parser.pprint_config(self.config["hdmodel"])
        logging.error("SECOND TIME!")
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
        for filetype in self.all_filetypes:
            # forcing_files = {'sst': 'pisst'}
            # forcing_sources = {'pisst': '/some/path/to/pisst_file/'}
            # forcing_in_work = {'sst': 'unit.24'}
            if filetype + "_sources" not in self.config:
                continue
            filedir_intermediate = getattr(self, "thisrun_" + filetype + "_dir")
            for file_descriptor, file_source in self.config[
                filetype + "_sources"
            ].items():
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
                if (
                    filetype + "_in_work" in self.config
                    and file_category in self.config[filetype + "_in_work"].keys()
                ):
                    # Cosmetic TODO: Give this dude a real name
                    file_target = (
                        filedir_intermediate
                        + "/"
                        + self.config[filetype + "_in_work"][file_category]
                    )
                else:
                    file_target = (
                        filedir_intermediate + "/" + os.path.basename(file_source)
                    )
                shutil.copy2(
                    file_source,
                    filedir_intermediate + "/" + os.path.basename(file_source),
                )
                if not os.path.isfile(file_target):
                    os.symlink(
                        filedir_intermediate + "/" + os.path.basename(file_source),
                        file_target,
                    )

    def other_stuff(self):
        for filetype in self.all_filetypes:
            setattr(
                self,
                "thisrun_" + filetype + "_dir",
                self.exp_base
                + "/"
                + self.expid
                + "/run_"
                + start_date
                + "-"
                + end_date
                + "/"
                + filetype
                + "/"
                + self.config["model"]
                + "/",
            )
            if not os.path.exists(getattr(self, "thisrun_" + filetype + "_dir")):
                os.makedirs(getattr(self, "thisrun_" + filetype + "_dir"))
