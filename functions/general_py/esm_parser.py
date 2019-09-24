#!/usr/bin/env python
"""
=======================================
``YAML`` Parser for Earth System Models
=======================================

One core element of the ``esm-tools`` is the description of model
configurations and experiments with the aid of ``YAML`` files. Beyond the
standard features of ``YAML``, several specific conventions have been
implemented to ease the description of your simulations. These conventions are
described below, and the functions which implement them are documented with
minimal examples. Internally, after parsing the ``YAML`` files are converted
into a single Python dictionary.

Parsing takes place by initializing objects which represent either an entire
setup, ``ConfigSetup``, or a specific component, ``ConfigComponent``. Both of
these objects base off of ``GeneralConfig``, which is a dictionary subclass
performing specific parsing steps during the object's creation. The parsing
steps are presented in the order that they are resolved:

When initializing a ``ConfigSetup`` or ``ConfigComponent``, a name of the
desired setup or component must be given, e.g. ``"awicm"`` or ``"echam"``. This
configuration is immediately loaded along with any further configs listed in
the section "further_reading". Note that this means that **any configuration
listed in "further_reading" must not contain any variables!!**

Following this step, a method called ``_config_init`` is run for all classes
based off of ``GeneralConfig``. For components, any entries listed under
``"include_submodels"`` are attached and registed under a new keyword
``"submodels"``.

For setups, the next step is to determine the computing host and load the
appropriate configuration files. Setups divide their configuration into 3
specific parts:

#. Setup information, contained under ``config['setup']``. This includes, e.g.
   information regarding a standalone setup, possible coupling, etc.
#. Model Information, under ``config['model']``. This contains specific
   information for all models and submodels, such as resolution, input file
   names, namelists, etc.
#. User information, under ``config['model']``. The user can specify to
   override any of the defaults with their own choices.

In the next step, all keys starting with ``"choose_"`` are determined, along
with any information they set. This is done first for the setup, and then for
the models. These are filtered to determine an independent choice, and if
cyclic dependencies occur, an error is raised. All choices are then resolved
until nothing is left.


-------

Specific documentation for classes and functions are given below:
"""
# Python 2 and 3 version agnostic compatiability:
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

# Python Standard Library imports
import collections
import copy
import logging
import os
import re
import shutil
import socket
import subprocess
import sys
import warnings

from pprint import pformat

import six

import esm_backwards_compatability
import esm_sim_objects

# Date class
from esm_calendar import Date

# Third-Party Imports
import coloredlogs
import yaml

# Logger and related constants
logger = logging.getLogger("root")
DEBUG_MODE = logger.level == logging.DEBUG
FORMAT = (
    "[%(asctime)s,%(msecs)03d:%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
)
f_handler = logging.FileHandler("file.log")
f_handler.setFormatter(FORMAT)
logger.addHandler(f_handler)


# Module Constants:
CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE = ["further_reading"]
DATE_MARKER = ">>>THIS_IS_A_DATE<<<"
FUNCTION_PATH = os.path.normpath(os.path.dirname(__file__) + "/../")
esm_master_dir = os.path.normpath(os.path.dirname(__file__) + "/../../")

YAML_AUTO_EXTENSIONS = ["", ".yml", ".yaml", ".YML", ".YAML"]

gray_list = [
    r"choose_lresume",
    r"choose_.*lresume",
    r"lresume",
    r".*date$",
    r".*date!(year|month|day|hour|minute|second)",
]
gray_list = [re.compile(entry) for entry in gray_list]


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
            logger.debug(
                "IOError (%s) File not found with %s, trying another extension pattern.",
                error.errno,
                filepath + extension,
            )
    raise FileNotFoundError(
        "All file extensions tried and none worked for %s" % filepath
    )


def pprint_config(config):  # pragma: no cover
    """
    Prints the dictionary given to the stdout in a nicely formatted YAML style.

    Parameters
    ----------
    config : dict
        The configuration to print

    Returns
    -------
    None
    """
    yaml.Dumper.ignore_aliases = lambda *args: True
    print(yaml.dump(config, default_flow_style=False))


def attach_to_config_and_reduce_keyword(
    config_to_read_from,
    config_to_write_to,
    full_keyword,
    reduced_keyword="included_files",
    level_to_write_to=None,
):
    """
    Attaches a new dictionary to the config, and registers it as the value of
    ``reduced_keyword``.

    Parameters
    ----------
    config_to_read_from : dict
        The configuration dictionary from which information is read from. The
        keyword from which additional YAML files are read from should be on the
        top level of this dictionary.
    config_to_write_to : dict
        The dictionary where the contents of
        ``config_to_read_from[full_keyword]`` is written in.
    full_keyword : 
        The keyword where contents are extracted from
    reduced_keyword :
        The keyword where the contents of ``config_to_read_from[full_keyword]``
        are written to
    level_to_write_to : 
        If this is specified, the attached entries are written here instead of
        in the top level of ``config_to_write_to``. Note that only one level
        down is currently supported.


    The purpose behind this is to have a chapter in config "include_submodels"
    = ["echam", "fesom"], which would then find the "echam.yaml" and
    "fesom.yaml" configs, and attach them to "config" under config[submodels],
    and the entire config for e.g. echam would show up in config[echam

    Since ``config_to_read_from`` and ``config_to_write_to`` are ``dict``
    objects, they are modified **in place**. Note also that the entry
    ``config_to_read_from[full_keyword]`` is deleted at the end of the routine.

    If the entry in ``config_to_read_from[full_keyword]`` is a list, each item
    in that list is split into two parts: ``model`` and ``model_part``. For example:

    >>> # Assuming: config_to_read_from[full_keyword] = ['echam.datasets', 'echam.restart.streams']
    >>> model, model_part = 'echam', 'datasets' # first part
    >>> model, model_part = 'echam', 'restart.streams' # second part

    The first part, in the example ``echam`` is used to determine where to look
    for new YAML files. Then, a yaml file corresponding to a file called
    ``echam.datasets.yaml`` is loaded, and attached to the config.

    Warning
    -------
    Both ``config_to_read_from`` and ``config_to_write_to`` are modified **in place**!
    """
    if full_keyword in config_to_read_from:
        if level_to_write_to:
            config_to_read_from[level_to_write_to][
                reduced_keyword
            ] = config_to_read_from[full_keyword]
        else:
            config_to_read_from[reduced_keyword] = config_to_read_from[full_keyword]
        # FIXME: Does this only need to work for lists?
        if isinstance(config_to_read_from[full_keyword], list):
            for item in config_to_read_from[full_keyword]:
                model, model_part = (item.split(".")[0], ".".join(item.split(".")[1:]))

                logger.debug("Reading %s", FUNCTION_PATH + "/" + model + "/" + item)
                tmp_config = yaml_file_to_dict(FUNCTION_PATH + "/" + model + "/" + item)

                logger.debug("Attaching: %s for %s", model_part, model)
                config_to_write_to[tmp_config["model"]] = tmp_config

                for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
                    logger.debug("Attaching: %s", attachment)
                    attach_to_config_and_remove(
                        config_to_write_to[tmp_config["model"]], attachment
                    )
        else:
            raise TypeError("The entries in %s must be a list!!" % full_keyword)
    del config_to_read_from[full_keyword]


def attach_single_config(config, attach_value):
    model, model_part = (
        attach_value.split(".")[0],
        ".".join(attach_value.split(".")[1:]),
    )
    logger.debug("Attaching: %s to %s", model, model_part)
    attachable_config = yaml_file_to_dict(
        FUNCTION_PATH + "/" + model + "/" + attach_value
    )
    config.update(attachable_config)


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

    Warning
    -------
    The ``config`` is modified **in place**!
    """
    if attach_key in config:
        attach_value = config[attach_key]
        if isinstance(attach_value, list):
            for attach_value in attach_value:
                attach_single_config(config, attach_value)
        elif isinstance(attach_value, str):
            attach_single_config(config, attach_value)
        else:
            raise TypeError("%s needs to have values of type list or str!" % attach_key)
        del config[attach_key]


def priority_merge_dicts(first_config, second_config, priority="first"):
    """Given two dictionaries, merge them together preserving either first or last entries.

    Parameters
    ----------
    first_config : dict
    second_config : dict
    priority : str
        One of "first" or "second". Specifies which dictionary should be given
        priority when merging.

    Returns
    -------
    merged : dict
        A dictionary containing all keys, with duplicate entries reverting to
        the dictionary given in "priority". The merge occurs across all levels.
    """
    if priority == "second":
        merged_dictionary = first_config
        to_merge = second_config
    elif priority == "first":
        merged_dictionary = second_config
        to_merge = first_config
    else:
        raise TypeError("Please use 'first' or 'second' for the priority!")
    for key in to_merge:
        if key in merged_dictionary:
            merged_dictionary[key].update(to_merge[key])
        else:
            merged_dictionary[key] = to_merge[key]

    return merged_dictionary


def check_conflicting_model_and_setup_names(config):
    all_names = list(config)
    all_model_names = config["general"]["valid_model_names"]
    for source_model in all_model_names:
        for target_model in all_names:
            if target_model in config[source_model]:
                raise KeyError(
                    "Please don't define %s in %s" % (target_model, source_model)
                )


def dict_merge(dct, merge_dct):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    for k, v in six.iteritems(merge_dct):
        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.Mapping)
        ):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]


def update_models_from_setup(config):
    all_model_names = config["general"]["valid_model_names"]
    for model_name in all_model_names:
        model_config_in_setup = config["general"].pop(model_name, {})
        dict_merge(config[model_name], model_config_in_setup)


def deep_update(
    chapter, entries, target_model, source_model, model_config, setup_config
):
    if target_model in model_config:
        target_config = model_config
    else:
        target_config = setup_config

    # Could be prettier:
    # target_config = model_config if target_model in model_config else setup_config
    # source_model = model_config if source_model in model_config else setup_config

    if source_model in model_config:
        source_config = model_config
    else:
        source_config = setup_config
    if chapter in source_config[source_model]:
        source_chapter = chapter
    else:
        source_chapter = chapter.replace(target_model + ".", "")

    if "remove_" in chapter:
        remove_entry_from_chapter(
            chapter, entries, target_model, source_model, model_config, setup_config
        )
    elif "add_" in chapter:
        add_entry_to_chapter(
            chapter, entries, target_model, source_model, model_config, setup_config
        )
    else:
        dict_merge(target_config[target_model], {chapter: entries})


def find_remove_entries_in_config(mapping, model_name):
    all_removes = []
    mappings = [mapping]
    while mappings:
        mapping = mappings.pop()
        try:
            items = six.iteritems(mapping)
        except AttributeError:
            continue
        for key, value in items:
            if isinstance(key, str) and key.startswith("remove_"):
                if not "." in key:
                    key = "remove_" + model_name + "." + key.split("remove_")[-1]
                all_removes.append((key, value))
            if isinstance(value, dict):
                mappings.append(value)
    # all_removes = [(remove_echam.forcing_files, [sst, sic,])]
    # NOTE: Not Allowed: all_removes = [(remove_echam.forcing_files, sst)]
    return all_removes


def remove_entry_from_chapter(
    remove_chapter,
    remove_entries,
    model_to_remove_from,
    model_with_remove_statement,
    model_config,
    setup_config,
):
    logging.debug("%s, %s", remove_entries, remove_chapter)
    if not isinstance(remove_entries, list):
        raise TypeError("Please put all entries to remove as a list")
    if model_to_remove_from in model_config:
        for entry in remove_entries:
            del model_config[model_to_remove_from][remove_chapter.split(".")[-1]][entry]
    elif model_to_remove_from in setup_config:
        for entry in remove_entries:
            del setup_config[model_to_remove_from][remove_chapter.split(".")[-1]][entry]
    if model_with_remove_statement in model_config:
        del model_config[model_with_remove_statement][
            remove_chapter.replace(model_with_remove_statement + ".", "")
        ]
    elif model_with_remove_statement in setup_config:
        del setup_config[model_with_remove_statement][
            remove_chapter.replace(model_with_remove_statement + ".", "")
        ]


def remove_entries_from_chapter_in_config(
    model_config, valid_model_names, setup_config, valid_setup_names
):
    for model_names, config in zip(
        [valid_model_names, valid_setup_names], [model_config, setup_config]
    ):
        for model in model_names:
            logging.debug(model)
            all_removes_for_model = find_remove_entries_in_config(config[model], model)
            for remove_chapter, remove_entries in all_removes_for_model:
                model_to_remove_from = remove_chapter.split(".")[0].replace(
                    "remove_", ""
                )
                remove_entry_from_chapter(
                    remove_chapter,
                    remove_entries,
                    model_to_remove_from,
                    model,
                    model_config,
                    setup_config,
                )


def find_add_entries_in_config(mapping, model_name):
    all_adds = []
    mappings = [mapping]
    while mappings:
        mapping = mappings.pop()
        try:
            items = six.iteritems(mapping)
        except AttributeError:
            continue
        for key, value in items:
            if isinstance(key, str) and key.startswith("add_"):
                if not "." in key:
                    key = "add_" + model_name + "." + key.split("add_")[-1]
                all_adds.append((key, value))
            if isinstance(value, dict):
                mappings.append(value)
    # all_adds = [(add_echam.forcing_files, [sst, sic,])]
    # NOTE: Not Allowed: all_adds = [(add_echam.forcing_files, sst)]
    return all_adds


def add_entry_to_chapter(
    add_chapter,
    add_entries,
    model_to_add_to,
    model_with_add_statement,
    model_config,
    setup_config,
):

    if model_to_add_to in model_config:
        target_config = model_config
    else:
        target_config = setup_config
    if model_with_add_statement in model_config:
        source_config = model_config
    else:
        cource_config = setup_config

    logging.debug(model_to_add_to)
    logging.debug(add_chapter)
    if add_chapter in source_config[model_with_add_statement]:
        source_chapter = add_chapter
    else:
        source_chapter = add_chapter.replace(model_to_add_to + ".", "")

    # If the desired chapter doesn't exist yet, just put it there
    logging.debug(model_to_add_to)
    logging.debug(add_chapter)
    if not target_config[model_to_add_to][
        add_chapter.split(".")[-1].replace("add_", "")
    ]:
        target_config[model_to_add_to][
            add_chapter.split(".")[-1].replace("add_", "")
        ] = source_config[model_with_add_statement][source_chapter]
    else:
        if not type(
            target_config[model_to_add_to][
                add_chapter.split(".")[-1].replace("add_", "")
            ]
        ) == type(add_entries):
            raise TypeError("Something is wrong")
        else:
            if isinstance(
                target_config[model_to_add_to][
                    add_chapter.split(".")[-1].replace("add_", "")
                ],
                list,
            ):
                method = "append"
            elif isinstance(
                target_config[model_to_add_to][
                    add_chapter.split(".")[-1].replace("add_", "")
                ],
                dict,
            ):
                method = "update"
            getattr(
                target_config[model_to_add_to][
                    add_chapter.split(".")[-1].replace("add_", "")
                ],
                method,
            )(add_entries)
    logging.debug(model_with_add_statement)
    logging.debug(source_chapter)
    # del source_config[model_with_add_statement][source_chapter.replace("add_", "")]


def add_entries_to_chapter_in_config(
    model_config, valid_model_names, setup_config, valid_setup_names
):
    for model_names, config in zip(
        [valid_model_names, valid_setup_names], [model_config, setup_config]
    ):
        for model in model_names:
            logging.debug(model)
            all_adds_for_model = find_add_entries_in_config(config[model], model)
            for add_chapter, add_entries in all_adds_for_model:
                model_to_add_to = add_chapter.split(".")[0].replace("add_", "")
                add_entry_to_chapter(
                    add_chapter,
                    add_entries,
                    model_to_add_to,
                    model,
                    model_config,
                    setup_config,
                )


def merge_dicts(*dict_args):
    """
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.

    Note that this function only merges the first level. For deeper merging,
    use ``priority_merge_dicts``.

    Parameters
    ----------
    *dict_args
        Any number of dictionaries to merge together

    Returns
    -------
    A merged dictionary (shallow).
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

    Warning
    -------
    The ``config`` is modified **in place**!
    """
    if key in config:
        del config[key]
    for v in config.values():
        if isinstance(v, dict):
            del_value_for_nested_key(v, key)


def find_value_for_nested_key(mapping, key_of_interest, tree=[]):
    """
    In a dict of dicts, find a value for a given key

    Parameters
    ----------
    mapping : dict
        The nested dictionary to search through
    key_of_interest : str
        The key to search for.
    tree : list
        Where to start searching

    Returns
    -------
    value :
        The value of key anywhere in the nested dict.

    Note
    ----
    Behaviour of what happens when a key appears twice anywhere on different
    levels of the nested dict is unclear. The uppermost one is taken, but if
    the key appears in more than one item, I'd guess something ambigous
    occus...
    """
    original_mapping = mapping
    logger.debug("Looking for key %s", key_of_interest)
    logging.debug("Looking in %s", mapping)
    logger.debug("Using tree %s", tree)
    if tree:
        for leaf in tree:
            mapping = mapping[leaf]
        else:
            tree = [None]
    for leaf in reversed(tree):
        logging.debug("Looking in bottommost leaf %s", leaf)
        for key, value in six.iteritems(mapping):
            if key == key_of_interest:
                return value
        if leaf:
            find_value_in_nested_key(original_mapping, key_of_interest, tree[:-1])
    warnings.warn("Couldn't find value for key %s" % key_of_interest)
    # raise KeyError("Couldn't find value for key %s", key_of_interest)


def list_all_keys_starting_with_choose(mapping, model_name, ignore_list, isblacklist):
    """
    Given a ``mapping`` (e.g. a ``dict``-type object), list all keys that start
    with ``"choose_"`` on any level of the nested dictionary.

    Parameters
    ----------
    mapping : dict
        The dictionary to search through for keys starting with ``"choose_"``

    model_name : str
    ignore_list : list
    Returns
    -------
    all_chooses : list
        A list of tuples for ....
        A dictionary containing all key, value pairs starting with
        ``"choose_"``.
    """
    logging.debug("Top of list_all_keys_starting_with_choose")
    all_chooses = []
    for key, value in six.iteritems(mapping):
        if (
            isinstance(key, str)
            and key.startswith("choose_")
            and (
                (not isblacklist)
                or (isblacklist and not determine_regex_list_match(key, ignore_list))
            )
        ):
            if not "." in key:
                old_key = key
                key = "choose_" + model_name + "." + key.split("choose_")[-1]
                del mapping[old_key]
                mapping[key] = value
            all_chooses.append((key, value))
    logging.debug("Will return %s", all_chooses)
    return all_chooses


def determine_set_variables_in_choose_block(config, valid_model_names, model_name=[]):
    """
    Given a config, figures out which variables are resolved in a choose block.

    In order to avoid cyclic dependencies, it is necessary to figure out which
    variables are set in which choose block. This function recurses over all
    key/value pairs of a configuration, and for any key which is a model name,
    it determines which variables are set in it's ``choose_`` blocks. Tuples of
    ``(model_name, var_name)`` are appended to a list, which is returned with
    all it's duplicates removed.

    Parameters
    ----------
    config : dict
    valid_model_names : list
    model_name : list

    Returns
    -------
    set_variables : list
        A list of tuples of model_name and corresponding variable that are
        determined in ``config``
    """
    set_variables = []
    for k, v in six.iteritems(config):
        if isinstance(k, str) and k in valid_model_names:
            logging.debug(k)
            model_name = k
        if isinstance(v, dict):  # and isinstance(k, str) and k.startswith("choose_"):
            # Go in further
            set_variables += determine_set_variables_in_choose_block(
                v, valid_model_names, model_name
            )
        else:
            var_name = k
            if not model_name:
                model_name = "general"
            set_variables.append((model_name, var_name))
    return set_variables


def find_one_independent_choose(all_set_variables):
    """
    Given a dictionary of ``all_set_variables``, which comes out of the
    function ``determine_set_variables_in_choose_block``, gives a list of
    task/variable dependencies to resolve in order to figure out the variable.

    Parameters
    ----------
    all_set_variables : dict

    Returns
    -------
    task_list : list
        A list of tuples comprising ``(model_name, var_name)`` in order to
        resolve one ``choose_`` block. This list is built in such a way that
        the beginning of the list provides dependencies for later on in the
        list.
    """
    task_list = []
    for key in all_set_variables:
        value = all_set_variables[key]
        for choose_keyword, set_vars in six.iteritems(value):
            task_list.append((key, choose_keyword))
            task_list = add_more_important_tasks(
                choose_keyword, all_set_variables, task_list
            )
            logging.debug(task_list)
            return task_list[0]


def resolve_choose(model_with_choose, choose_key, config):
    if model_with_choose in config:
        config_to_replace_in = config
    else:
        raise KeyError("Something is horribly wrong")
    model_name, key = choose_key.replace("choose_", "").split(".")
    choice = config.get(model_with_choose).get(key)
    if isinstance(choice, str) and "${" in choice:
        logging.warn("Variable %s as a choice, skipping...", choice)
        del config_to_replace_in[model_with_choose][choose_key]
        return
    logging.debug(choice)

    config_to_search_in = {}

    if model_name in config:
        config_to_search_in = config

    if not config_to_search_in:
        raise KeyError("Something else is horribly wrong")

    if key in config_to_search_in[model_name]:
        choice = config_to_search_in[model_name][key]
        logging.debug(model_with_choose)
        logging.debug(choice)

        if choice in config_to_replace_in[model_with_choose][choose_key]:
            for update_key, update_value in six.iteritems(
                config_to_replace_in[model_with_choose][choose_key][choice]
            ):
                deep_update(
                    update_key,
                    update_value,
                    model_with_choose,
                    model_with_choose,
                    config,
                    config,
                )

        elif "*" in config_to_replace_in[model_with_choose][choose_key]:
            logging.debug("Found a * case!")
            for update_key, update_value in six.iteritems(
                config_to_replace_in[model_with_choose][choose_key]["*"]
            ):
                deep_update(
                    update_key,
                    update_value,
                    model_with_choose,
                    model_with_choose,
                    config,
                    config,
                )
        else:
            logging.warning("Choice %s could not be resolved", choice)
            logging.warning("Key was key=%s", key)
        logging.debug("key=%s", key)
    elif "*" not in config_to_replace_in[model_with_choose][choose_key]:
        raise KeyError("Key %s was not defined", key)
    del config_to_replace_in[model_with_choose][choose_key]


def add_more_important_tasks(choose_keyword, all_set_variables, task_list):
    """
    Determines dependencies of a choose keyword.

    Parameters
    ----------
    choose_keyword : str
        The keyword, starting with choose, which is looked through to check if
        there are any dependencies that must be resolved first to correctly
        resolve this one.
    all_set_variables : dict
        All variables that can be set
    task_list : list
        A list in the order in which tasks must be resolved for
        ``choose_keyword`` to make sense.

    Returns
    -------
    task_list
        A list of choices which must be made in order for choose_keyword to
        make sense.
    """
    keyword = choose_keyword.replace("choose_", "")
    for model in all_set_variables:
        for choose_thing in all_set_variables[model]:
            logging.debug("Choose_thing = %s", choose_thing)
            for (host, keyword_that_is_set) in all_set_variables[model][choose_thing]:
                if keyword_that_is_set == keyword:
                    if (model, choose_thing) not in task_list:
                        task_list.insert(0, (model, choose_thing))
                        add_more_important_tasks(
                            choose_thing, all_set_variables, task_list
                        )
                        return task_list
                    else:
                        raise KeyError("Opps cyclic dependency: %s" % task_list)
    return task_list


def recursive_run_function(tree, right, level, func, *args, **kwargs):
    """ Recursively runs func on all nested dicts.

    Tree is a list starting at the top of the config dictionary, where it will
    be labeled "top"

    Parameters
    ----------
    tree : list
        Where in the dictionary you are
    right :
        The value of the last key in `tree`
    level : str, one of "mappings", "atomic", "always"
        When to perform func
    func : callable
        An function to perform on all levels where the type of ``right`` is in
        ``level``. See the Notes for how this function's call signature should
        look.
    *args :
        Passed to func
    **kwargs :
        Passed to func

    Returns
    -------
    right

    Note
    ----
    The ``func`` argument must be a callable (i.e. a function) and **must**
    have a call signature of the following form:

    .. code::

        def func(tree, right, *args, **kwargs(

    """
    # logging.debug("Top of function")
    # logging.debug("tree=%s", tree)
    if level == "mappings":
        do_func_for = [dict, list]
    elif level == "atomic":
        do_func_for = [str, int, float]
        if six.PY2:
            do_func_for.append(unicode)
    elif level == "always":
        do_func_for = [str, dict, list, int, float, bool]
    elif level == "keys":
        do_func_for = []
    else:
        do_func_for = []

    # Python 2/3 error in YAML parser, bad workaround:
    if six.PY2:
        if isinstance(right, unicode):
            logging.warn("Unicode type detected, converting to a regular string!")
            right = right.encode("utf-8")
            assert isinstance(right, str)
            logging.warn(right)

    logging.debug("Type right: %s", type(right))
    logging.debug("Do func for: %s", do_func_for)

    if level is "keys" and isinstance(right, dict):
        keys = list(right)
        for key in keys:
            old_value = right[key]
            returned_key = func(tree + [key], key, *args, **kwargs)
            del right[key]
            right.update({returned_key: old_value})

    # logger.debug("right is a %s!", type(right))
    if type(right) in do_func_for:
        if isinstance(right, dict):
            keys = list(right)
            for key in keys:
                value = right[key]
                logger.debug("Deleting key %s", key)
                logging.debug(
                    "Start func %s with %s, %s sent from us",
                    func.__name__,
                    tree + [key],
                    value,
                )
                returned_dict = func(tree + [key], value, *args, **kwargs)
                del right[key]
                # logger.debug("Back out of func %s", func.__name__)
                # logger.debug("Got as returned_dict: %s", returned_dict)
                right.update(returned_dict)
        elif isinstance(right, list):
            for index, item in enumerate(right):
                del right[index]
                right.append(func(tree + [None], item, *args, **kwargs))
        else:
            right = func(tree + [None], right, *args, **kwargs)

    # logger.debug("finished with do_func_for")

    if isinstance(right, list):
        for index, item in enumerate(right):
            new_item = recursive_run_function(
                tree + [None], item, level, func, *args, **kwargs
            )
            right[index] = new_item
    elif isinstance(right, dict):
        keys = list(right)
        for key in keys:
            value = right[key]
            right[key] = recursive_run_function(
                tree + [key], value, level, func, *args, **kwargs
            )
    return right


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
    logging.debug("Incoming config elements: %s", config_elements)
    this_config = config_elements.pop(0)

    logger.debug("this_config=%s", this_config)
    logger.debug("config_to_search=%s", config_to_search)
    result = config_to_search.get(this_config, None)
    if result is None:
        raise ValueError("Exactly None! Couldn't find an answer for:", config_elements)
    # This looks dangerous too...
    if config_elements:
        return recursive_get(result, config_elements)
    return result


def determine_regex_list_match(test_str, regex_list):
    result = []
    for regex in regex_list:
        logging.debug("Checking %s against %s", test_str, regex)
        result.append(regex.match(test_str))
    logging.debug("Will return %s" % any(result))
    return any(result)


def find_variable(tree, rhs, full_config, white_or_black_list, isblacklist):
    raw_str = rhs
    if isinstance(raw_str, str) and "${" in raw_str:
        ok_part, rest = raw_str.split("${", 1)
        var, new_raw = rest.split("}", 1)
        if (determine_regex_list_match(var, white_or_black_list)) != isblacklist:
            var_result = actually_find_variable(tree, var, full_config)
            if var_result:
                ok_part, var_result, more_rest = (
                    str(ok_part),
                    str(var_result),
                    str(new_raw),
                )
                logger.debug("Will replace again: %s", ok_part + var_result + more_rest)
                return find_variable(
                    tree,
                    ok_part + var_result + more_rest,
                    full_config,
                    white_or_black_list,
                    isblacklist,
                )

                # if new_raw:
                #    more_rest = find_variable(
                #        tree, new_raw, full_config, white_or_black_list, isblacklist
                #    )
                # else:
                #    more_rest = ""
                ## Make sure everything is a string:
                # return ok_part + var_result + more_rest
    return raw_str


def actually_find_variable(tree, rhs, full_config):
    config_elements = rhs.split(".")
    valid_names = list(full_config)
    logging.debug(valid_names)
    if config_elements[0] not in valid_names:
        config_elements.insert(0, tree[0])

    original_config_elements = copy.deepcopy(config_elements)
    try:
        var_result = recursive_get(full_config, config_elements)
        return var_result
    except ValueError:
        # Maybe it is in the general:
        try:
            config_elements = original_config_elements
            logging.debug(config_elements)
            config_elements[0] = "general"
            var_result = recursive_get(full_config, config_elements)
            return var_result
        except:
            raise ValueError("Sorry: %s not found" % (rhs))


constant_replace_dict = {"${expid}": "TEST_EXPID"}


def replace_constants(tree, rhs, config):
    if not tree[-1]:
        tree = tree[:-1]
    lhs = tree[-1]
    entry = rhs
    # FIXME(PG): I don't like have this duplicate code here...
    if isinstance(raw_str, str) and "${" in raw_str:
        ok_part, rest = raw_str.split("${", 1)
        var, new_raw = rest.split("}", 1)
        if (determine_regex_list_match(var, white_or_black_list)) != isblacklist:
            # var_result =
            if var_result:
                if new_raw:
                    more_rest = find_variable(
                        tree, new_raw, full_config, white_or_black_list, isblacklist
                    )
                else:
                    more_rest = ""
                # Make sure everything is a string:
                ok_part, var_result, more_rest = (
                    str(ok_part),
                    str(var_result),
                    str(more_rest),
                )
                logger.debug("Will return: %s", ok_part + var_result + more_rest)
                return ok_part + var_result + more_rest
    return raw_str

    if entry in list(constant_replace_dict):
        entry = constant_replace_dict[entry]
    return entry


def list_to_multikey(tree, rhs, config_to_search):
    """
    A recursive_run_function conforming func which puts any list based key to a
    multikey elsewhere. Sorry, that sounds confusing even to me, and I wrote
    the function.

    Parameters
    ----------
    tree : list

    rhs : str

    config_to_search : dict



    """
    if tree:
        lhs = tree[-1]
        list_fence = "[["
        list_end = "]]"
        if isinstance(lhs, str) and lhs:
            if list_fence in lhs:
                return_dict = {}
                ok_part, rest = lhs.split(list_fence, 1)
                actual_list, new_raw = rest.split(list_end, 1)
                key_in_list, value_in_list = actual_list.split("-->", 1)
                key_elements = key_in_list.split(".")
                entries_of_key = actually_find_variable(
                    tree, key_in_list, config_to_search
                )
                if isinstance(rhs, str):
                    return_dict2 = {}
                    for key in entries_of_key:
                        return_dict2[lhs.replace("[[" + actual_list + "]]", key).replace(value_in_list, key)] = rhs.replace(value_in_list, key)

                if isinstance(rhs, list):
                    replaced_list = []
                    for item in rhs:
                        if isinstance(item, str):
                            for key in entries_of_key:
                                replaced_list.append(item.replace(value_in_list, key))
                        else:
                            replaced_list.append(item)
                    return_dict2 = {
                        lhs.replace("[[" + actual_list + "]]", key).replace(
                            value_in_list, key
                        ): replaced_list
                        for key in entries_of_key
                    }

                if list_fence in new_raw:
                    for key, value in six.iteritems(return_dict2):
                        return_dict.update(
                            list_to_multikey(tree + [key], value, config_to_search)
                        )
                else:
                    return_dict = return_dict2
                return return_dict
            return {lhs: rhs}
        if isinstance(rhs, str) and list_fence in rhs:
            rhs_list = []
            ok_part, rest = rhs.split(list_fence, 1)
            actual_list, new_raw = rest.split(list_end, 1)
            key_in_list, value_in_list = actual_list.split("-->", 1)
            key_elements = key_in_list.split(".")
            entries_of_key = actually_find_variable(tree, key_in_list, config_to_search)
            for entry in entries_of_key:
                rhs_list.append(
                    rhs.replace("[[" + actual_list + "]]", entry).replace(
                        value_in_list, entry
                    )
                )
            if list_fence in new_raw:
                out_list = []
                for rhs_listitem in rhs_list:
                    out_list += list_to_multikey(
                        tree + [None], rhs_listitem, config_to_search
                    )
                rhs_list = out_list
            return rhs_list
        elif isinstance(lhs, bool):
            return {lhs: rhs}
    return rhs


def determine_computer_from_hostname():
    """
    Determines which yaml config file is needed for this computer

    Notes
    -----
    The supercomputer must be registered in the ``all_machines.yaml`` file in
    order to be found.

    Returns
    -------
    str
        A string for the path of the computer specific yaml file.
    """
    # FIXME: This needs to be a resource file at some point
    all_computers = yaml_file_to_dict(FUNCTION_PATH + "/machines/all_machines.yaml")
    for this_computer in all_computers:
        for computer_pattern in all_computers[this_computer].values():
            if isinstance(computer_pattern, str):
                if re.match(computer_pattern, socket.gethostname()):
                    return FUNCTION_PATH + "/machines/" + this_computer + ".yaml"
            elif isinstance(computer_pattern, (list, tuple)):
                # Pluralize to avoid confusion:
                computer_patterns = computer_pattern
                for pattern in computer_patterns:
                    if re.match(pattern, socket.gethostname()):
                        return FUNCTION_PATH + "/machines/" + this_computer + ".yaml"
    print ("The yaml file for this computer (%s) could not be determined!" % socket.gethostname())
    print ("Continuing with generic settings...")
    return FUNCTION_PATH + "/machines/generic.yaml"

    #raise FileNotFoundError(
    #    "The yaml file for this computer (%s) could not be determined!"
    #    % socket.gethostname()
    #)


def do_math_in_entry(tree, rhs, config):
    if not tree[-1]:
        tree = tree[:-1]
    entry = rhs
    if "${" in str(entry):
        return entry
    entry = " " + str(entry) + " "
    while "$((" in entry:
        math, after_math = entry.split("))", 1)
        math, before_math = math[::-1].split("(($", 1)
        math = math[::-1]
        before_math = before_math[::-1]
        if DATE_MARKER in math:
            all_dates = []
            steps = math.split(" ")
            steps = [step for step in steps if step]
            math = ""
            index = 0
            for step in steps:
                if step in ["+", "-"]:
                    math = math + step
                else:
                    all_dates.append(Date(step.replace(DATE_MARKER, "")))
                    math = math + "all_dates[" + str(index) + "]"
                    index += 1
        result = str(eval(math))
        entry = before_math + result + after_math
    return entry.strip()


def mark_dates(tree, rhs, config):
    """Adds the ``DATE_MARKER`` to any entry who's key ends with ``"date"``"""
    if not tree[-1]:
        tree = tree[:-1]
    lhs = tree[-1]
    entry = rhs
    logging.debug(entry)
    if "${" in str(entry):
        return entry
    if isinstance(lhs, str) and lhs.endswith("date"):
        entry = str(entry) + DATE_MARKER
    return entry


def marked_date_to_date_object(tree, rhs, config):
    """Transforms a marked date string into a Date object"""
    if not tree[-1]:
        tree = tree[:-1]
    lhs = tree[-1]
    entry = rhs
    if isinstance(entry, Date):
        return entry
    if "${" in str(entry):
        return entry
    if isinstance(lhs, str) and lhs.endswith("date"):
        # if isinstance(entry, str) and DATE_MARKER in entry and "<--" not in entry:
        while DATE_MARKER in entry:
            entry = entry.replace(DATE_MARKER, "")
            if "!" in entry:
                actual_date, date_attr = entry.split("!", 1)
            else:
                actual_date, date_attr = entry, None
            entry = Date(actual_date)
            if date_attr:
                rentry = []
                for attr in date_attr.split("!"):
                    rentry.append(str(getattr(entry, attr)))
                return "".join(rentry)
            else:
                return entry.output()
    return entry


def unmark_dates(tree, rhs, config):
    """Removes the ``DATE_MARKER`` to any entry who's entry contains the ``DATE_MARKER``."""
    if not tree[-1]:
        tree = tree[:-1]
    lhs = tree[-1]
    entry = rhs
    if isinstance(entry, str) and DATE_MARKER in entry:
        entry = entry.replace(DATE_MARKER, "")
    return entry


class GeneralConfig(dict):
    """ All configs do this! """

    def __init__(self, path, user_config):
        super(dict, self).__init__()
        if os.path.isfile(path):
            config_path = path
        else:
            config_path = FUNCTION_PATH + "/" + path + "/" + path
        self.config = yaml_file_to_dict(config_path)
        for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
            attach_to_config_and_remove(self.config, attachment)
        self._config_init(user_config)
        for k, v in six.iteritems(self.config):
            self.__setitem__(k, v)
        del self.config

    def _config_init(self, user_config):
        raise NotImplementedError(
            "Subclasses of GeneralConfig must define a _config_init!"
        )


class ConfigSetup(GeneralConfig):
    """ Config Class for Setups """

    def _config_init(self, user_config):
        setup_config = {
            "computer": yaml_file_to_dict(determine_computer_from_hostname()),
            "general": {},
        }
        # Add the fake "model" name to the computer:
        setup_config["computer"]["model"] = "computer"
        logger.info("setup config is being updated with setup_relevant_configs")

        model_config = {}

        if "coupled_setup" not in self.config:
            setup_config["general"]["include_models"] = self.config["include_models"]
            setup_config["general"].update({"standalone": True})
        else:
            setup_config["general"] = self.config
            setup_config["general"].update({"standalone": False})
        del self.config
        attach_to_config_and_reduce_keyword(
            setup_config["general"], model_config, "include_models", "models"
        )
        for model in setup_config["general"]["models"]:
            attach_to_config_and_reduce_keyword(
                model_config[model], model_config, "include_models", "models"
            )
        setup_config["general"] = {"esm_master_dir": esm_master_dir, "expid": "test"}
        setup_config["general"]["valid_setup_names"] = valid_setup_names = list(
            setup_config
        )
        setup_config["general"]["valid_model_names"] = valid_model_names = list(
            model_config
        )
        logging.debug("Valid Setup Names = %s", valid_setup_names)
        logging.debug("Valid Model Names = %s", valid_model_names)

        self.config = priority_merge_dicts(user_config, setup_config, priority="first")
        self.config = priority_merge_dicts(self.config, model_config, priority="first")

        check_conflicting_model_and_setup_names(self.config)
        update_models_from_setup(self.config)

        self.choose_blocks(self.config)
        self.run_recursive_functions(self.config)

    def choose_blocks(self, config, isblacklist=True):
        valid_setup_names = config["general"]["valid_setup_names"]
        valid_model_names = config["general"]["valid_model_names"]
        all_set_variables = {}

        all_names = valid_setup_names + valid_model_names
        for name in all_names:
            while True:
                all_set_variables[name] = {}
                name_chooses = list_all_keys_starting_with_choose(
                    config[name], name, gray_list, isblacklist
                )
                if name_chooses == []:
                    break
                for key, block in name_chooses:
                    all_set_variables[name][
                        key
                    ] = determine_set_variables_in_choose_block(block, all_names, name)

                task_list = model_with_choose, choose_key = find_one_independent_choose(
                    all_set_variables
                )
                logging.debug("The task list is: %s", task_list)
                logging.debug("all_set_variables: %s", all_set_variables)
                resolve_choose(model_with_choose, choose_key, config)
                del all_set_variables[model_with_choose][choose_key]
                for key in list(all_set_variables):
                    if not all_set_variables[key]:
                        del all_set_variables[key]
                logging.debug("Remaining all_set_variables=%s", all_set_variables)

        add_entries_to_chapter_in_config(
            config, valid_model_names, config, valid_setup_names
        )
        remove_entries_from_chapter_in_config(
            config, valid_model_names, config, valid_setup_names
        )

    def run_recursive_functions(self, config, isblacklist=True):
        logging.debug("Top of run recursive functions")
        recursive_run_function([], config, "atomic", mark_dates, config)
        recursive_run_function(
            [],
            config,
            "atomic",
            find_variable,
            config,
            gray_list,
            isblacklist=isblacklist,
        )
        recursive_run_function(
            [],
            config,
            "keys",
            find_variable,
            config,
            gray_list,
            isblacklist=isblacklist,
        )
        recursive_run_function([], config, "atomic", do_math_in_entry, config)
        recursive_run_function([], config, "atomic", unmark_dates, config)
        recursive_run_function([], config, "atomic", marked_date_to_date_object, config)
        recursive_run_function([], config, "always", list_to_multikey, config)


# PG: Delete this:
if __name__ == "__main__":  # pragma: no cover

    import argparse

    def parse_args():
        """ The arg parser for interactive use """
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-d",
            "--debug",
            help="Print lots of debugging statements",
            action="store_const",
            dest="loglevel",
            const=logging.DEBUG,
            default=logging.ERROR,
        )
        parser.add_argument(
            "-v",
            "--verbose",
            help="Be verbose",
            action="store_const",
            dest="loglevel",
            const=logging.INFO,
        )
        parser.add_argument("runscript", default=None)
        return parser.parse_args()

    # Set up a useful logger
    ARGS = parse_args()
    coloredlogs.install(fmt=FORMAT, level=ARGS.loglevel)
    # logging.basicConfig(format=FORMAT, level=ARGS.loglevel)

    logger.info("Working here: %s", os.getcwd())
    logger.info("This file is here: %s", os.path.dirname(__file__))
    logger.info(
        "The main function directory should be: %s",
        os.getcwd() + "/" + os.path.dirname(__file__) + "/../",
    )

    Script = esm_backwards_compatability.ShellscriptToUserConfig(ARGS.runscript)
    Setup = esm_sim_objects.SimulationSetup(
        Script["general"]["setup_name"].replace("_standalone", ""), Script
    )
    Setup.prepare()
