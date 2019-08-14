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
import copy
import collections
import logging
import os
import re
import shutil
import socket
import warnings

from builtins import dict
from builtins import open
from builtins import super
from future import standard_library
from pprint import pformat

# Date class
from esm_calendar import Date

# Third-Party Imports
import coloredlogs
import yaml

logger = logging.getLogger("root")
FORMAT = (
    "[%(asctime)s,%(msecs)03d:%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
)
f_handler = logging.FileHandler("file.log")
f_handler.setFormatter(FORMAT)
logger.addHandler(f_handler)


standard_library.install_aliases()


CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE = ["further_reading"]
FUNCTION_PATH = os.path.dirname(__file__) + "/../"
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
            logger.debug(
                "IOError (%s) File not found with %s, trying another extension pattern.",
                error.errno,
                filepath + extension,
            )
    raise FileNotFoundError(
        "All file extensions tried and none worked for %s" % filepath
    )


def pprint_config(config):
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

    Note
    ----
    Both ``config_to_read_from`` and ``config_to_write_to`` are modified **in place**!
    """
    if full_keyword in config_to_read_from:
        if level_to_write_to:
            config_to_write_to[level_to_write_to][
                reduced_keyword
            ] = config_to_read_from[full_keyword]
        else:
            config_to_write_to[reduced_keyword] = config_to_read_from[full_keyword]
        # FIXME: Does this only need to work for lists?
        if isinstance(config_to_read_from[full_keyword], list):
            for item in config_to_read_from[full_keyword]:
                # Suffix fix, this could be smarter:
                model, model_part = (item.split(".")[0], ".".join(item.split(".")[1:]))
                logger.debug("Attaching: %s for %s", model_part, model)
                #
                tmp_config = yaml_file_to_dict(FUNCTION_PATH + "/" + model + "/" + item)
                config_to_write_to[tmp_config["model"]] = tmp_config
                # config[item] = yaml_file_to_dict(loadable_item)
                for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
                    logger.debug("Attaching: %s", attachment)
                    attach_to_config_and_remove(
                        config_to_write_to[tmp_config["model"]], attachment
                    )
    del config_to_read_from[full_keyword]


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
                model, model_part = (
                    attach.split(".")[0],
                    ".".join(attach.split(".")[1:]),
                )
                logger.debug("Attaching: %s to %s", model, model_part)
                attachable_config = yaml_file_to_dict(
                    FUNCTION_PATH + "/" + model + "/" + attach
                )
                config.update(attachable_config)
        elif isinstance(attach_value, str):
            attachable_config = yaml_file_to_dict(attach_value)
            config.update(attachable_config)
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


def cross_update_models(model_config, all_model_names):
    for target_model_name in all_model_names:
        for source_model_name in all_model_names:
            while target_model_name in model_config[source_model_name]:
                logging.debug(
                    "Updating %s from info of %s", target_model_name, source_model_name
                )
                logging.debug(
                    "Info to be sent: %s",
                    model_config[source_model_name][target_model_name],
                )
                model_config[target_model_name].update(
                    model_config[source_model_name][target_model_name]
                )
                logging.debug(
                    "Deleting info %s from %s", target_model_name, source_model_name
                )
                del model_config[source_model_name][target_model_name]


def update_models_from_setup(
    setup_config, all_setup_names, model_config, all_model_names
):
    for target_model_name in all_model_names:
        for source_setup_name in all_setup_names:
            while target_model_name in setup_config[source_setup_name]:
                model_config[target_model_name].update(
                    setup_config[source_setup_name][target_model_name]
                )
                del setup_config[source_setup_name][target_model_name]


def find_remove_entries_in_config(mapping, model_name):
    all_removes = []
    mappings = [mapping]
    while mappings:
        mapping = mappings.pop()
        try:
            items = mapping.items()
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
        logging.debug(target_model)
        logging.debug(chapter)
        logging.debug(entries)
        target_config[target_model].update({chapter: entries})


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
            items = mapping.items()
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

    Note
    ----
    The ``config`` is modified **in place**!.
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
        for key, value in mapping.items():
            if key == key_of_interest:
                return value
        if leaf:
            find_value_in_nested_key(original_mapping, key_of_interest, tree[:-1])
    warnings.warn("Couldn't find value for key %s" % key_of_interest)
    # raise KeyError("Couldn't find value for key %s", key_of_interest)


# def deep_update(dict_original, dict_new):


def list_all_keys_starting_with_choose(mapping, model_name):
    """
    Given a ``mapping`` (e.g. a ``dict``-type object), list all keys that start
    with ``"choose_"`` on any level of the nested dictionary.

    Parameters
    ----------
    mapping : dict
        The dictionary to search through for keys starting with ``"choose_"``

    Returns
    -------
    all_chooses : list
        A list of tuples for ....
        A dictionary containing all key, value pairs starting with
        ``"choose_"``.
    """
    all_chooses = []
    mappings = [mapping]
    while mappings:
        mapping = mappings.pop()
        try:
            items = mapping.items()
        except AttributeError:
            continue
        for key, value in items:
            if isinstance(key, str) and key.startswith("choose_"):
                if not "." in key:
                    key = "choose_" + model_name + "." + key.split("choose_")[-1]
                all_chooses.append((key, value))
            if isinstance(value, dict):
                mappings.append(value)
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
    logging.debug("valid_model_names=%s", valid_model_names)
    for k, v in config.items():
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
                model_name = "setup"
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
    # task_list=['choose_partition', 'choose_jobtype']
    for key in all_set_variables:
        value = all_set_variables[key]
        for choose_keyword, set_vars in value.items():
            # choose_keyword="choose_partition"
            # set_vars=value[choose_keyword]
            task_list.append((key, choose_keyword))
            task_list = add_more_important_tasks(
                choose_keyword, all_set_variables, task_list
            )
            logging.debug(task_list)
            return task_list[0]


def resolve_choose(model_with_choose, choose_key, setup_config, model_config):
    if model_with_choose in setup_config:
        config_to_replace_in = setup_config
    elif model_with_choose in model_config:
        config_to_replace_in = model_config
    else:
        raise KeyError("Something is horribly wrong")
    model_with_choose_key = choose_key.replace("choose_", "").split(".")[0]
    if model_with_choose_key in setup_config:
        config_to_search_in = setup_config
    elif model_with_choose_key in model_config:
        config_to_search_in = model_config
    else:
        raise KeyError("Something else is horribly wrong")

    model_name, key = choose_key.replace("choose_", "").split(".")
    pprint_config(config_to_replace_in)
    choice = config_to_search_in[model_name][key]

    logging.debug(model_with_choose)
    logging.debug(choice)

    if choose_key in config_to_replace_in[model_with_choose]:
        logging.debug("Case A")
        key = choose_key
    else:
        logging.debug("Case B")
        key = choose_key.replace(model_name + ".", "")

    for update_key, update_value in config_to_replace_in[model_with_choose][key][
        choice
    ].items():
        deep_update(
            update_key,
            update_value,
            model_with_choose,
            model_with_choose,
            model_config,
            setup_config,
        )

    logging.debug("key=%s", key)

    #    config_to_replace_in[model_with_choose].update(
    #        config_to_replace_in[model_with_choose][key][choice]
    #    )

    del config_to_replace_in[model_with_choose][key]


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
    logging.debug("Incoming task list %s", task_list)
    keyword = choose_keyword.replace("choose_", "")
    logging.debug("Keyword = %s", keyword)
    for model in all_set_variables:
        for choose_thing in all_set_variables[model]:
            logging.debug("Choose_thing = %s", choose_thing)
            for (host, keyword_that_is_set) in all_set_variables[model][choose_thing]:
                logging.debug(
                    "Host = %s, keyword_that_is_set=%s", host, keyword_that_is_set
                )
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


def make_choices_new(tree, right, full_config):
    """
    Replaces keys starting with ``"choose_"`` with an appropriate choice.

    If any key in the right hand side starts with ``"choose_"``, the full
    configuration is searched for a resolution of this choice. The right hand
    side is then appropriately updated.

    Parameters
    ----------
    tree : list
        The list of addresses up to this point
    right : dict
        An object that needs to be updated with a choice
    full_config :
        The entire configuration to search through

    Returns
    -------
    dict :
        A dictionary with the last part of ``tree`` and an updated version of
        the ``right`` dictionary in which choices have been performed.
    """
    logger.debug("Tree=%s, right=%s", tree, right)
    # logging.debug("Full config I am choosing in=%s", full_config)
    if not tree[-1]:
        tree = tree[:-1]
    if isinstance(right, dict):
        for key in list(right):
            if isinstance(key, str) and key.startswith("choose_"):
                logger.debug("Choosing key: %s", key)
                available_choices = right[key]
                del right[key]
                choice = find_value_for_nested_key(
                    full_config, key.replace("choose_", ""), tree
                )
                if available_choices:
                    logger.debug("Available choices: %s", available_choices)
                    logger.debug("Choice: %s", choice)
                    logger.debug("Updating right with %s", available_choices[choice])
                    right.update(available_choices[choice])
    return {tree[-1]: right}


def recursive_run_function_lhs(right, func, left, *args, **kwargs):
    """ Recursively runs func on all nested dicts """

    if isinstance(right, list):
        for index, item in enumerate(right):
            new_item = recursive_run_function_lhs(item, func, None, *args, **kwargs)
            right[index] = new_item
    elif isinstance(right, dict):
        keys = list(right)
        for key in keys:
            value = right[key]
            right[key] = recursive_run_function_lhs(value, func, key, *args, **kwargs)
    # BUG: What about str and tuple? We only specifically handle list and dict
    # here, is that OK?
    else:
        right = func(right, left, *args, **kwargs)
        # raise TypeError("Needs str, list, or dict")
    return right


def recursive_run_function_new(tree, right, level, func, *args, **kwargs):
    """ Recursively runs func on all nested dicts.

    Tree is a list starting at the top of the config dictionary, where it will be labeled "top"

    Parameters
    ----------
    tree : list
        Where in the dictionary you are
    right :
        The value of the last key in `tree`
    level : str, one of "mappings", "atomic", "always"
        When to perform func
    func : callable
        An function to perform on all levels where the type of ``right`` is in ``level``.
    *args :
        Passed to func
    **kwargs :
        Passed to func

    Returns
    -------
    right
    """
    logging.debug("Top of function")
    logging.debug("tree=%s", tree)
    if level is "mappings":
        do_func_for = [dict, list]
    elif level is "atomic":
        do_func_for = [str, int, float]
    elif level is "always":
        do_func_for = [str, dict, list, int, float, bool]
    else:
        do_func_for = []

    # def func(tree, right, *args, **kwargs):

    logger.debug("right is a %s!", type(right))
    if type(right) in do_func_for:
        logger.debug("It's in %s", do_func_for)
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
                logger.debug("Back out of func %s", func.__name__)
                logger.debug("Got as returned_dict: %s", returned_dict)
                right.update(returned_dict)
        elif isinstance(right, list):
            for index, item in enumerate(right):
                del right[index]
                right.append(func(tree + [None], item, *args, **kwargs))
        else:
            right = func(tree + [None], right, *args, **kwargs)

    logger.debug("finished with do_func_for")

    if isinstance(right, list):
        for index, item in enumerate(right):
            new_item = recursive_run_function_new(
                tree + [None], item, level, func, *args, **kwargs
            )
            right[index] = new_item
    elif isinstance(right, dict):
        keys = list(right)
        for key in keys:
            value = right[key]
            right[key] = recursive_run_function_new(
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
    # NOTE(PG) I really don't like the logic in this function... :-( It'd be
    # much cleaner if this one and actually_recursive_get could be combined...
    this_config = config_elements.pop(0)

    logger.debug("this_config=%s", this_config)

    result = config_to_search.get(this_config, None)
    if not result:
        raise ValueError("Couldn't find an answer for:", config_elements)
    if config_elements:
        return recursive_get(result, config_elements)
    return result


def find_variable(tree, rhs, full_config):
    raw_str = rhs
    if isinstance(raw_str, str) and "${" in raw_str:
        ok_part, rest = raw_str.split("${", 1)
        var, new_raw = rest.split("}", 1)
        var_result = actually_find_variable(tree, var, full_config)
        if var_result:
            if new_raw:
                more_rest = find_variable(tree, new_raw, full_config)
            else:
                more_rest = ""
            # Make sure everything is a string:
            ok_part, var_result, more_rest = (
                str(ok_part),
                str(var_result),
                str(more_rest),
            )
            logger.debug("Will return:", ok_part + var_result + more_rest)
            return ok_part + var_result + more_rest
    return raw_str


def actually_find_variable(tree, rhs, full_config):
    config_elements = rhs.split(".")
    valid_names = (
        full_config["setup"]["valid_model_names"]
        + full_config["setup"]["valid_setup_names"]
    )
    logging.debug(valid_names)
    if config_elements[0] not in valid_names:
        config_elements.insert(0, tree[0])

    # if config_elements[0] in ["setup"]:
    #     del config_elements[0]
    # elif config_elements[0] in [
    #     "computer",
    #     full_config["model"],
    #     full_config["submodels"],
    # ]:
    #     pass
    # else:
    #     try:
    #         raw_str = tree[0] + "." + rhs
    #         return actually_find_variable(tree, raw_str, full_config)
    #     except:
    #         pass
    try:
        var_result = recursive_get(full_config, config_elements)
        return var_result
    except ValueError:
        raise ValueError("Sorry: %s not found" % (rhs))


def list_to_multikey_lhs(tree, rhs, config_to_search):
    logging.debug("tree=%s", tree)
    logging.debug("rhs=%s", rhs)
    if tree:
        lhs = tree[-1]
        list_fence = "[["
        list_end = "]]"
        logging.debug("Running list_to_multikey_lhs")
        logging.debug("lhs=%s", lhs)
        logging.debug(type(lhs))
        logging.debug("rhs=%s", rhs)
        logging.debug(type(rhs))
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
                    return_dict2 = {
                        lhs.replace("[[" + actual_list + "]]", key).replace(
                            value_in_list, key
                        ): rhs.replace(value_in_list, key)
                        for key in entries_of_key
                    }
                if isinstance(rhs, list):
                    replaced_list = []
                    for item in rhs:
                        if isinstance(item, str):
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
                    for key, value in return_dict2.items():
                        return_dict.update(
                            list_to_multikey_lhs(tree + [key], value, config_to_search)
                        )
                else:
                    return_dict = return_dict2
                logging.debug("About to return: %s", return_dict)
                return return_dict
            logging.debug("About to return: %s", {lhs: rhs})
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
                    out_list += list_to_multikey_lhs(
                        tree + [None], rhs_listitem, config_to_search
                    )
                    logging.debug(out_list)
                rhs_list = out_list
            return rhs_list
    return rhs


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
                logger.debug("Passing %s=%s down to %s", k, v, thing_below)
                # this_thing["inherited_attrs"][k] = v  # if k not in config[key]
                this_thing[k] = v  # PG: I'm not 100% sure here, but it seems to work?
            else:
                logger.debug("%s already has an attribute %s", thing_below, k)
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
    raise FileNotFoundError(
        "The yaml file for this computer (%s) could not be determined!"
        % socket.gethostname()
    )


# NOTE: This whole function is just way too weird for me...
def do_math_in_entry(entry, lhs):
    entry = " " + str(entry) + " "
    while "$((" in entry:
        math, after_math = entry.split("))", 1)
        # Math becomes reversed -- I don't remember why
        math, before_math = math[::-1].split("(($", 1)
        # Reverse both math and before_math back to original form.
        math = math[::-1]
        before_math = before_math[::-1]
        ## Now we want to actually do math
        if date_marker in math:
            all_dates = []
            steps = math.split(" ")
            # Remove emtpy strings from the list
            steps = [step for step in steps if step]
            math = ""
            index = 0
            for step in steps:
                if step in ["+", "-"]:
                    math = math + step
                else:
                    all_dates.append(Date(step.replace(date_marker, "")))
                    math = math + "all_dates[" + str(index) + "]"
                    index += 1
        result = str(eval(math))
        entry = before_math + result + after_math
    return entry.strip()


date_marker = ">>>THIS_IS_A_DATE<<<"


def mark_dates(entry, lhs, config):
    """Adds the ``date_marker`` to any entry who's key ends with ``"date"``"""
    if isinstance(lhs, str) and lhs.endswith("date"):
        entry = str(entry) + date_marker
    return entry


def unmark_dates(entry, lhs, config):
    """Removes the ``date_marker`` to any entry who's entry contains the ``date_marker``."""
    if isinstance(entry, str) and date_marker in entry:
        entry = entry.replace(date_marker, "")
    return entry


class GeneralConfig(dict):
    """ All configs do this! """

    def __init__(self, path):
        super().__init__()
        config_path = FUNCTION_PATH + "/" + path + "/" + path
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


class ConfigTest(GeneralConfig):
    def _config_init(self):
        setup_relevant_configs = {
            "computer": yaml_file_to_dict(determine_computer_from_hostname())
        }
        self.config = merge_dicts(setup_relevant_configs, self.config)


class SimulationSetup(object):
    def __init__(self, name):
        self.config = ConfigSetup(name)
        pprint_config(self.config)
        components = []
        for component in self.config["setup"]["valid_model_names"]:
            components.append(SimulationComponent(self.config[component]))


class SimulationComponent(object):
    def __init__(self, config):
        self.config = config

        self.exp_base = "/tmp/example_experiments/"
        self.expid = "test"
        start_date = "18500101"
        end_date = "18510101"

        self.all_filetypes = [
            "forcing",
            "config",
            "input",
            "restart",
            "outdata",
            "log",
            "mon",
            "analysis",
            "bin",
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


class ConfigSetup(GeneralConfig):
    """ Config Class for Setups """

    def _config_init(self):
        setup_relevant_configs = {
            "computer": yaml_file_to_dict(determine_computer_from_hostname())
        }
        # Add the fake "model" name to the computer:
        setup_relevant_configs["computer"]["model"] = "computer"
        logger.info("setup config is being updated with setup_relevant_configs")
        if "standalone_model" in self.config:
            setup_config = setup_relevant_configs
            if "setup" not in setup_config:
                setup_config["setup"] = {}
            setup_config["setup"].update({"standalone": True})
            model_config = {}
            model_config[self.config["model"]] = self.config
            attach_to_config_and_reduce_keyword(
                model_config[self.config["model"]],
                model_config,
                "include_submodels",
                "submodels",
                self.config["model"],
            )
            del self.config
        else:
            setup_config = merge_dicts(self.config, setup_relevant_configs)
            model_config = {}
            attach_to_config_and_reduce_keyword(
                setup_config, model_config, "include_models", "models"
            )
            for model in model_config["models"]:
                logger.info("Updating dictionary for ", model)
                tmp_config = ConfigComponent(model)
                model_config[model] = merge_dicts(tmp_config, model_config[model])

        valid_setup_names = list(setup_config)
        valid_model_names = list(model_config)

        setup_config["setup"]["valid_setup_names"] = valid_setup_names
        setup_config["setup"]["valid_model_names"] = valid_model_names

        logging.debug("Valid Setup Names = %s", valid_setup_names)
        logging.debug("Valid Model Names = %s", valid_model_names)

        all_set_variables = {}
        for setup_name in valid_setup_names:
            all_set_variables[setup_name] = {}
            logging.debug(
                list_all_keys_starting_with_choose(setup_config[setup_name], setup_name)
            )
            for choose_key, choose_block in list_all_keys_starting_with_choose(
                setup_config[setup_name], setup_name
            ):
                logging.debug("%s %s %s", setup_name, choose_key, choose_block)
                all_set_variables[setup_name][
                    choose_key
                ] = determine_set_variables_in_choose_block(
                    choose_block, valid_setup_names, model_name=setup_name
                )

        for model_name in valid_model_names:
            all_set_variables[model_name] = {}
            for choose_key, choose_block in list_all_keys_starting_with_choose(
                model_config[model_name], model_name
            ):
                all_set_variables[model_name][
                    choose_key
                ] = determine_set_variables_in_choose_block(
                    choose_block, valid_model_names, model_name=model_name
                )

        self.all_set_variables = all_set_variables

        for components_with_set_variables in self.all_set_variables:
            logging.debug(
                "The simulation component %s has to set:"
                % components_with_set_variables
            )
            for set_variable in self.all_set_variables[components_with_set_variables]:
                logging.debug("A variable to be set is %s", set_variable)

        task_list = find_one_independent_choose(all_set_variables)
        logging.debug("The task list is: %s", task_list)

        # for model_name in valid_model_names:
        #    all_set_variables[model_name] = {}
        #    for choose_key, choose_block in list_all_keys_starting_with_choose(model_config[model_name]).items():
        #        logging.debug("%s %s %s", setup_name, choose_key, choose_block)
        #        all_set_variables[model_name][choose_key]['set_vars'] = determine_set_variables_in_choose_block(
        #            choose_block, valid_model_names, model_name=model_name
        #        all_set_variables[model_name][choose_key]['source_model']=determine_source_model(choose_key, model_name, valid_setup_names, valid_model_names)
        #        )
        logging.debug("all_setup_variables %s", all_set_variables)

        set_variables = all_set_variables
        logging.debug(set_variables)
        while True:
            model_with_choose, choose_key = find_one_independent_choose(set_variables)

            resolve_choose(model_with_choose, choose_key, setup_config, model_config)
            del set_variables[model_with_choose][choose_key]
            for key in list(set_variables):
                if not set_variables[key]:
                    del set_variables[key]
            logging.debug("Remaining set_variables=%s", set_variables)
            if not set_variables:
                break

        cross_update_models(model_config, valid_model_names)
        update_models_from_setup(
            setup_config, valid_setup_names, model_config, valid_model_names
        )

        logging.debug("Setup after cross update:")
        pprint_config(setup_config)
        logging.debug("Model after cross update:")
        pprint_config(model_config)

        add_entries_to_chapter_in_config(
            model_config, valid_model_names, setup_config, valid_setup_names
        )
        remove_entries_from_chapter_in_config(
            model_config, valid_model_names, setup_config, valid_setup_names
        )

        logging.debug("Setup before priority merge:")
        pprint_config(setup_config)
        logging.debug("Model before priority merge:")
        pprint_config(model_config)
        self.model_config = model_config
        self.setup_config = setup_config
        self.user_config = {}  # TODO read runscript to dict
        self.config = priority_merge_dicts(
            self.user_config, self.setup_config, priority="first"
        )
        self.config = priority_merge_dicts(
            self.config, self.model_config, priority="first"
        )
        logging.debug("After priority merge:")
        pprint_config(self.config)

        # recursive_run_function_lhs(
        #    self.config, mark_dates, self.config["model"], self.config
        # )

        recursive_run_function_new(
            [], self.config, "atomic", find_variable, self.config
        )

        # recursive_run_function_lhs(
        #    self.config, find_variable, self.config["model"], self.config
        # )
        # recursive_run_function_lhs(self.config, do_math_in_entry, self.config["model"])

        # recursive_run_function_lhs(
        #    self.config, unmark_dates, self.config["model"], self.config
        # )

        recursive_run_function_new(
            [], self.config, "always", list_to_multikey_lhs, self.config
        )


class ConfigComponent(GeneralConfig):
    """ Config class for components """

    def _config_init(self):
        attach_to_config_and_reduce_keyword(
            self.config, "include_submodels", "submodels"
        )


if __name__ == "__main__":

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
            default=logging.WARNING,
        )
        parser.add_argument(
            "-v",
            "--verbose",
            help="Be verbose",
            action="store_const",
            dest="loglevel",
            const=logging.INFO,
        )
        parser.add_argument("setup", default=None)
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

    if ARGS.setup:
        SETUP = SimulationSetup(ARGS.setup)
        yaml.Dumper.ignore_aliases = lambda *args: True
        print(yaml.dump(SETUP.config, default_flow_style=False))
