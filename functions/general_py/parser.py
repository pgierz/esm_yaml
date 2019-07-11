#!/usr/bin/env python
"""
Docs
"""
# Python 2 and 3 version agnostic compatiability:
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

# Python Standard Library imports
import collections
import logging
import os
import re
import socket
import warnings

from builtins import dict
from builtins import open
from builtins import super
from future import standard_library


# Date class
from esm_calendar import Date

# Third-Party Imports
import yaml

standard_library.install_aliases()

CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE = ["further_reading"]
YAML_AUTO_EXTENSIONS = ["", ".yml", ".yaml", ".YML", ".YAML"]


def yaml_file_to_dict(filepath):
    """
    Given a yaml file, returns a corresponding dictionary.

    If you do not give an extension, tries again after appending one.

    Parameters
    ----------
    filepath : str
        Where to get the YAML file from

    Returns
    -------
    dict
        A dictionary representation of the yaml file.
    """
    for extension in YAML_AUTO_EXTENSIONS:
        try:
            with open(filepath + extension) as yaml_file:
                return yaml.load(yaml_file, Loader=yaml.FullLoader)
        except IOError as error:
            logging.debug(
                "(%s) File not found with %s, trying another extension pattern.",
                error.errno,
                filepath + extension,
            )
    raise FileNotFoundError(
        "All file extensions tried and none worked for %s" % filepath
    )


def attach_to_config_and_reduce_keyword(config, full_keyword, reduced_keyword="included_files"):
    """
    Attaches a new dictionary to the config, and registers it as the value of
    ``reduced_keyword``.

    The purpose behind this is to have a chapter in config "include_submodels"
    = ["echam", "fesom"], which would then find the "echam.yaml" and
    "fesom.yaml" configs, and attach them to "config" under config[submodels],
    and the entire config for e.g. echam would show up in config[echam]
    """
    if full_keyword in config:
        config[reduced_keyword] = config[full_keyword]
        # FIXME: Does this only need to work for lists?
        if isinstance(config[full_keyword], list):
            for item in config[full_keyword]:
                # Suffix fix, this could be smarter:
                loadable_item = item if item.endswith(".yaml") else item + ".yaml"
                # BUG
                model, model_part = loadable_item.split(".")[0], ".".join(loadable_item.split(".")[1:]) 
                print("Attaching:", model, model_part)
                #
                #print("Will try to load:", loadable_item)
                tmp_config = yaml_file_to_dict(FUNCTION_PATH+"/"+model+"/"+loadable_item)
                config[tmp_config['model']] = tmp_config
                #config[item] = yaml_file_to_dict(loadable_item)
                for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
                    print("Attaching:", attachment)
                    attach_to_config_and_remove(config[tmp_config['model']], attachment)
    del config[full_keyword]


def attach_to_config_and_remove(config, attach_key):
    """
    Attaches extra dict to this one and removes the chapter

    Updates the dictionary on ``config`` with values from any file found under
    a listing specified by ``attach_key``.

    Parameters
    ----------
    config : dict
        The configuration to update
    attach_key : str
        A key who's value points to a list of various yaml files to update
        ``config`` with.

    Note
    ----
    The ``config`` is modified **in place**!.
    """
    if attach_key in config:
        attach_value = config[attach_key]
        if isinstance(attach_value, list):
            for attach in attach_value:
                model, model_part = attach.split(".")[0], ".".join(attach.split(".")[1:]) 
                print("Attaching:", model, model_part)
                attachable_config = yaml_file_to_dict(FUNCTION_PATH+"/"+model+"/"+attach)
                config.update(attachable_config)
        elif isinstance(attach_value, str):
            attachable_config = yaml_file_to_dict(attach_value)
            config.update(attachable_config)
        else:
            raise TypeError("%s needs to have values of type list or str!" % attach_key)
        del config[attach_key]


def flatten_bottom_up(dictionary):
    """
    Flattens a nested dictionary, keeping the innermost values for repeated keys.

    Parameters
    ----------
    dictionary : dict
        The dictionary to flatten

    Returns
    -------
    A new, flattened dictionary.

    Examples
    --------
    >>> example_dict = {
    ...     'top_level': {
    ...             'sounds': {
    ...                 'dog': 'bark',
    ...                 'bear': 'growl',
    ...                 'cat': 'meow',
    ...                 'lion': 'roar',
    ...                 },
    ...             'actions': {
    ...                 'fish': 'swim',
    ...                 'bird': 'fly',
    ...                 'a': {
    ...                     'dog': 'whine',
    ...                     'fish': 'bubbles',
    ...                     'cat': 'purr',
    ...                     }
    ...                 },
    ...             'places': {
    ...                 'animals': {
    ...                     'bird': 'sky',
    ...                     'fish': 'ocean',
    ...                     'cat': 'indoors',
    ...                     'lion': 'zoo'
    ...                     }
    ...                 }
    ...             }
    ...     }
    >>> flatten_bottom_up(example_dict)
    {'dog': 'whine', 'bear': 'growl', 'cat': 'indoors', 'lion': 'zoo', 'fish': 'ocean', 'bird': 'sky'}
    """
    output = dict()
    for k, v in dictionary.items():
        if isinstance(v, dict):
            output.update(flatten_bottom_up(v))
        else:
            output[k] = v
    return output


def flatten_top_down(dictionary):
    """
    Flattens a nested dictionary, keeping the outermost values for repeated keys

    Parameters
    ----------
    dictionary : dict
        The dictionary to flatten

    Returns
    -------
    A new, flattened dictionary.

    Examples
    --------
    >>> example_dict = {
    ...     'top_level': {
    ...             'sounds': {
    ...                 'dog': 'bark',
    ...                 'bear': 'growl',
    ...                 'cat': 'meow',
    ...                 'lion': 'roar',
    ...                 },
    ...             'actions': {
    ...                 'fish': 'swim',
    ...                 'bird': 'fly',
    ...                 'a': {
    ...                     'dog': 'whine',
    ...                     'fish': 'bubbles',
    ...                     'cat': 'purr',
    ...                     }
    ...                 },
    ...             'places': {
    ...                 'animals': {
    ...                     'bird': 'sky',
    ...                     'fish': 'ocean',
    ...                     'cat': 'indoors',
    ...                     'lion': 'zoo'
    ...                     }
    ...                 }
    ...             }
    ...     }
    >>> flatten_top_down(example_dict)
    {'dog': 'bark', 'bear': 'growl', 'cat': 'meow', 'lion': 'roar', 'fish': 'swim', 'bird': 'fly'}
    """
    output = dict()
    for k, v in dictionary.items():
        if isinstance(v, dict):
            inner_dict = flatten_top_down(v)
            for inner_k, inner_v in inner_dict.items():
                if inner_k not in output:
                    output[inner_k] = inner_v
        elif k not in output:
            output[k] = v
    return output


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


def del_value_for_nested_key(config, key):
    """
    In a dict of dicts, delete a key/value pair.

    Parameters
    ----------
    config : dict
        The dict to delete in.
    key : str
        The key to delete.

    Note
    ----
    The ``config`` is modified **in place**!.
    """
    if key in config:
        del config[key]
    for v in config.values():
        if isinstance(v, dict):
            del_value_for_nested_key(v, key)


def find_value_for_nested_key(config, key):
    """
    In a dict of dicts, find a value for a given key

    Parameters
    ----------
    config : dict
        The nested dictionary to search through
    key : str
        The key to search for.

    Returns
    -------
    The value of key anywhere in the nested dict.

    Note
    ----
    Behaviour of what happens when a key appears twice anywhere on different
    levels of the nested dict is unclear. The uppermost one is taken, but if
    they key appears in more than one item, I'd guess something ambigous
    occus...
    """
    if key in config:
        return config[key]
    for v in config.values():
        if isinstance(v, dict):
            print("Next level down, now looking for %s in:" % key, v)
            return find_value_for_nested_key(v, key)
    print("WARNING!!!")
    return None  # NOTE: This **should** never happen...?


def make_choice_in_config(config, key, first_time=True):
    """
    Given a specific ``config``, pulls out the corresponding choices for ``key``.

    If a ``config`` dictionary has (key, value) pairs in the form of
    ``key=choose_<key>, value=<dict of choices>``, this function mutates the
    ``config`` dictionary so that the values fitting to ``choose_<key>[key]``
    are placed in ``config``. The entire ``choose_<key>`` entry is then
    deleted.

    Parameters
    ----------
    config : dict
        The dictionary to replace choices in.
    key : str
        The key to choose. Note here to use just the short part of the key,
        e.g. ``'resolution'`` and not ``'choose_resolution'``.
    """
    logging.debug("Trying to make choice for >>%s<<", key)
    choice = find_value_for_nested_key(config, key)
    try:
        config.update(config["choose_" + key][choice])
        del config["choose_" + key]
    except KeyError:
        if not first_time:
            warnings.warn("Could not find a choice for %s (yet)" % key)






def recursive_make_choices(config, first_time=True):
    """Recursively calls make choices for any dict in config"""
    all_config_keys = list(config)
    for k in all_config_keys:
        v = config[k]
        if isinstance(k, str) and k.startswith("choose_"):
            make_choice_in_config(
                config, k.replace("choose_", ""), first_time=first_time
            )
        if isinstance(v, dict):
            recursive_make_choices(v)


def recursive_run_function_lhs(config, func, last_key, *args, **kwargs):
    """ Recursively runs func on all nested dicts """

    if isinstance(config, list):
        for index, item in enumerate(config):
            logging.debug("In a list!")
            new_item = recursive_run_function_lhs(item, func, None, *args, **kwargs)
            config[index] = new_item
    elif isinstance(config, dict):
        keys = list(config)
        for key in keys:
            value = config[key]
            logging.debug("In a dict!")
            config[key] = recursive_run_function_lhs(value, func, key, *args, **kwargs)
    # BUG: What about str and tuple? We only specifically handle list and dict
    # here, is that OK?
    else:
        logging.debug("In an atomic thing")
        config = func(config, last_key, *args, **kwargs)
        # raise TypeError("Needs str, list, or dict")
    return config



def recursive_get(config_to_search, config_elements):
    """
    Recusively gets entries in a nested dictionary in the form ``outer_key.middle_key.inner_key = value``

    Given a list of config elements in the form above (e.g. the result of
    splitting the string ``"outer_key.middle_key.inner_key".split(".")``` on
    the dot), the value "value" of the innermost nest is returned. 

    Parameters
    ----------
    config_to_search : dict
        The dictionary to search through
    config_elements : list
        Each part of the next level of the dictionary to search, as a list.

    Returns
    -------
        The value associated with the nested dictionary specified by ``config_elements``.

    Note
    ----
        This is actually just a wrapper around the function
        ``actually_recursive_get``, which is needed to pop off standalone model
        configurations.
    """
    # NOTE(PG) I really don't like the logic in this function... :-( It'd be
    # much cleaner if this one and actually_recursive_get could be combined...
    if config_to_search["model"] == config_elements[0] or config_elements[0] == "setup":
        # Throw away the first thing:
        print("Throwing away the first part of config_elements")
        print("Before:", config_elements)
        config_elements.pop(0)
        print("After:", config_elements)
    return actually_recursive_get(config_to_search, config_elements)

def actually_recursive_get(config_to_search, config_elements):
    """
    See the documentation for ``recursive_get``.
    """
    this_config = config_elements.pop(0)
    result = config_to_search.get(this_config)
    if not result:
        raise ValueError
    if config_elements:
        return actually_recursive_get(result, config_elements)
    return result


def find_variable(raw_str, lhs, config_to_search):
    if isinstance(raw_str, str) and "${" in raw_str:
        ok_part, rest = raw_str.split("${", 1)
        var, new_raw = rest.split("}", 1)
        config_elements = var.split(".")
        original_search = var
        if len(config_elements) == 1:
            try:
                raw_str = ok_part + "${" + config_to_search["model"] + "." + rest
                return find_variable(raw_str, lhs, config_to_search)
            except:
                pass
        if config_elements[0] == "setup":
            config_elements = config_elements[1:]
        print("Split the string on .")
        print(config_elements)
        try:
            var_result = recursive_get(config_to_search, config_elements)
        except ValueError:
            logging.error("I was looking in this dict:")
            yaml.Dumper.ignore_aliases = lambda *args: True
            print(yaml.dump(config_to_search, default_flow_style=False))
            raise ValueError("Sorry: %s not found" % (original_search))

        if var_result:
            if new_raw:
                more_rest = find_variable(new_raw, lhs, config_to_search)
            else:
                more_rest = ""
            # Make sure everything is a string:
            ok_part = str(ok_part)
            var_result = str(var_result)
            more_rest = str(more_rest)
            print("Will return:", ok_part + var_result + more_rest)
            return ok_part + var_result + more_rest
        warnings.warn("Maybe look in the other config")
    return raw_str


def pass_down(config, key):
    """
    Passes attributes downwards.
    """
    for thing_below in config[key]:
        this_thing = config[thing_below]
        this_thing.setdefault("inherited_attrs", {})
        this_thing.setdefault("progenitor_attrs", {})
        popped_thing_below = config.pop(thing_below)
        for k, v in config.items():
            # This next part is still a bit confusing, but it looks like it
            # works...?
            if k not in config[key] and k not in this_thing and k != key:
                logging.debug("Passing %s=%s down to %s", k, v, thing_below)
                # this_thing["inherited_attrs"][k] = v  # if k not in config[key]
                this_thing[k] = v  # PG: I'm not 100% sure here, but it seems to work?
            else:
                logging.debug("%s already has an attribute %s", thing_below, k)
                # this_thing["progenitor_attrs"][k] = [v]
        config[thing_below] = popped_thing_below


def determine_computer_from_hostname():
    """
    Determines which yaml config file is needed for this computer

    Returns
    -------
    str
        A string for the path of the computer specific yaml file.
    """
    # FIXME: This needs to be a resource file at some point
    all_computers = yaml_file_to_dict(FUNCTION_PATH+"/machines/all_machines.yaml")
    for this_computer in all_computers:
        for computer_pattern in all_computers[this_computer].values():
            if isinstance(computer_pattern, str):
                if re.match(computer_pattern, socket.gethostname()):
                    return FUNCTION_PATH+"/machines/"+this_computer + ".yaml"
            elif isinstance(computer_pattern, (list, tuple)):
                # Pluralize to avoid confusion:
                computer_patterns = computer_pattern
                for pattern in computer_patterns:
                    if re.match(pattern, socket.gethostname()):
                        return FUNCTION_PATH+"/machines/"+this_computer + ".yaml"
    raise FileNotFoundError(
        "The yaml file for this computer (%s) could not be determined!"
        % socket.gethostname()
    )


def do_math_in_entry(entry, lhs):
    entry = " " + str(entry) + " "
    while "$((" in entry:
        math, after_math = entry.split("))", 1)

        print("after first step: math=", math, "after_math=", after_math)
        math, before_math = math[::-1].split("(($", 1)
        math = math[::-1]
        before_math = before_math[::-1]

        ## Now we want to actually do math
        if date_marker in math:
            all_dates = []
            steps = math.split(" ")
            print(steps)
            new_steps = []
            for step in steps:
                if step:
                    new_steps.append(step)
            steps = new_steps
            print(steps)
            math = ""
            index = 0
            for step in steps:
                print(index, "-->", step)
                if step in ["+", "-"]:
                    math = math + step
                else:
                    print("Making a Date out of", step.replace(date_marker, ""))
                    all_dates.append(Date(step.replace(date_marker, "")))
                    math = math + "all_dates[" + str(index) + "]"
                    index += 1

        print(math)
        result = str(eval(math))
        entry = before_math + result + after_math
    return entry.strip()


date_marker = "THIS_IS_A_DATE_JKLJKLJKL"


def mark_dates(entry, lhs, config):
    if isinstance(lhs, str) and lhs.endswith("date"):
        entry = str(entry) + date_marker
    return entry


def unmark_dates(entry, lhs, config):
    if isinstance(entry, str) and entry.endswith(date_marker):
        entry = entry.replace(date_marker, "")
    return entry


class GeneralConfig(dict):
    """ All configs do this! """

    def __init__(self, path):
        super().__init__()
        config_path = FUNCTION_PATH+"/"+path+"/"+path
        self.config = yaml_file_to_dict(config_path)
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
        if "standalone_model" in self.config:
            # NOTE: This could have cleaner sytnax is only Python > 3.5: c =
            # {**a, **b}, for now we use a function
            self.config = merge_dicts(setup_relevant_configs, self.config)
            attach_to_config_and_reduce_keyword(
                self.config, "include_submodels", "submodels"
            )
            #self.config = merge_dicts(
            #    setup_relevant_configs, ConfigComponent(self.config["model"])
            #)
            recursive_make_choices(self.config)
            logging.debug("Unordered DICT, try again!")
            # Since the dictionary resolves choices in an unordered way, there
            # might still be unresolved choices.
            #
            # To resolve, do the pass down again:
            # pass_down(self.config, "submodels")
            # And re-resolve choices:
            recursive_make_choices(self.config, first_time=False)
        else:
            self.config = merge_dicts(self.config, setup_relevant_configs)
            attach_to_config_and_reduce_keyword(self.config, "include_models", "models")
            for model in self.config["models"]:
                if model in self.config:
                    print("Updating dictionary for ", model)
                    tmp_config = ConfigComponent(model)
                    self.config[model] = merge_dicts(tmp_config, self.config[model])
                else:
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
        # pass_down(self.config, "submodels")
        recursive_make_choices(self.config)


if __name__ == "__main__":

    import argparse

    print("Working here:", os.getcwd())
    print("This file is here:", os.path.dirname(__file__))

    print("The main function directory should be:", os.getcwd()+"/"+os.path.dirname(__file__)+"/../")

    FUNCTION_PATH = os.getcwd()+"/"+os.path.dirname(__file__)+"/../"

    def parse_args():
        """ The arg parser for interactive use """
        parser = argparse.ArgumentParser()
        parser.add_argument("--run_tests", action="store_true")
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("setup", default=None)
        return parser.parse_args()

    ARGS = parse_args()
    if ARGS.run_tests:
        import doctest

        doctest.testmod()
        # TODO: Have something that runs unit tests

    if ARGS.debug:
        logging.basicConfig(level=logging.DEBUG)

    if ARGS.setup:
        CFG = ConfigSetup(ARGS.setup)
        yaml.Dumper.ignore_aliases = lambda *args: True
        print(yaml.dump(CFG, default_flow_style=False))
