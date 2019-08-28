"""
Documentation goes here
"""
import os
import shutil

import esm_parser


class SimulationSetup(object):
    def __init__(self, name, user_config):
        self.config = esm_parser.ConfigSetup(name, user_config)
        components = []
        for component in self.config["setup"]["valid_model_names"]:
            components.append(SimulationComponent(self.config[component]))
        del user_config


class SimulationComponent(object):
    def __init__(self, config):
        self.config = config

        self.exp_base = "/tmp/example_experiments/"
        self.expid = "test"
        start_date = "18500101"
        end_date = "18510101"

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
            "scripts",
            "viz",
        ]

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

            setattr(
                self,
                "experiment_" + filetype + "_dir",
                self.exp_base
                + "/"
                + self.expid
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
