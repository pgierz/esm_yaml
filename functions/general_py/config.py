class GeneralConfig(dict):
    """ All configs do this! """

    def __init__(self, path):
        super().__init__()
        self.config = yaml_file_to_dict(path)
        for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
            attach_to_config_and_remove(self.config, attachment)
        self._config_init()
        for k, v in self.config.items():
            self.__setitem__(k, v)
        del self.config

    def _config_init(self):
        raise NotImplementedError(
            "Subclasses of GeneralConfig must define a _config_init!"
        )


class ConfigSetup(GeneralConfig):
    """ Config Class for Setups """

    def _config_init(self):
        setup_relevant_configs = {
            "computer": yaml_file_to_dict(determine_computer_from_hostname())
        }
        recursive_promote_all(setup_relevant_configs)
        if "standalone_model" in self.config:
            # NOTE: This could have cleaner sytnax is only Python > 3.5: c =
            # {**a, **b}, for now we use a function
            self.config = merge_dicts(
                setup_relevant_configs, ConfigComponent(self.config["model"])
            )
            recursive_make_choices(self.config)
            logging.debug("Unordered DICT, try again!")
            # Since the dictionary resolves choices in an unordered way, there
            # might still be unresolved choices.
            #
            # To resolve, do the pass down again:
            pass_down(self.config, "submodels")
            # And re-resolve choices:
            recursive_make_choices(self.config, first_time=False)
        else:
            attach_to_config_and_reduce_keyword(self.config, "include_models", "models")
            for model in self.config["models"]:
                self.config[model] = ConfigComponent(model)
        recursive_run_function_lhs(
            self.config, mark_dates, self.config["model"], self.config
        )
        recursive_run_function_lhs(
            self.config, find_variable, self.config["model"], self.config
        )
        recursive_run_function_lhs(self.config, do_math_in_entry, self.config["model"])

        recursive_run_function_lhs(
            self.config, unmark_dates, self.config["model"], self.config
        )


class ConfigComponent(GeneralConfig):
    """ Config class for components """

    def _config_init(self):
        attach_to_config_and_reduce_keyword(
            self.config, "include_submodels", "submodels"
        )
        pass_down(self.config, "submodels")
        recursive_make_choices(self.config)
