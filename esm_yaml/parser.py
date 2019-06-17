"""
Docs
"""

# Python Standard Library imports
import collections
import logging
import re
import socket
import warnings

# Third-Party Imports
import yaml

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
        except FileNotFoundError:
            logging.debug(
                "File not found with %s, trying another extension pattern." % filepath
                + extension
            )
    raise FileNotFoundError(
        "All file extensions tried and none worked for %s" % filepath
    )


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
                attachable_config = yaml_file_to_dict(attach)
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
            find_value_for_nested_key(v, key)
    return None  # NOTE: This **should** never happen...?


def make_choice_in_config(config, key):
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
    logging.debug("Trying to make choice for %s", key)
    choice = find_value_for_nested_key(config, key)
    if not isinstance(choice, collections.Hashable):
        choice = freeze(choice)
    del_value_for_nested_key(config, key)
    if "choose_" + key in config:
        try:
            # FIXME: Why are strs different than any other thing that could be
            # in choice? I had a reason, but I can't remember right now...
            if not isinstance(choice, str):
                logging.debug(
                    "config[%s] = dict(%s=config['choose_'+%s][%s])",
                    key,
                    choice,
                    key,
                    choice,
                )
                config[key] = {choice: config["choose_" + key][choice]}
            else:
                config[key] = choice
            del config["choose_" + key]
        except KeyError:
            warnings.warn("Could not find a choice for %s" % key)


def promote_value_to_key(config, promotable_key):
    """
    Moves values for ``promotable_key`` to the top of the ``config``
    dictionary.

    Parameters
    ----------
    config : dict
        The dictionary to promote things in
    promotable_key : str
        The key in the outermost dictionary which should be replaced with
        interiour information.

    Returns
    -------
    str :
        The key which was promoted.

    Warns
    -----
    Throws a warning if the promotable key couldn't be found in this config.
    """
    for key in list(config):
        value = config[key]
        if key == "promote_" + promotable_key and isinstance(value, dict):
            for inner_key, inner_value in value.items():
                if inner_key == config[promotable_key]:
                    config.update(inner_value)
                    del config["promote_" + promotable_key]
                    return promotable_key
            warnings.warn(
                "Couldn't find promotable key %s in %s"
                % (config[promotable_key], value)
            )


def promote_all(config):
    """
    Promotes everything in a specific config

    Since the promotions inside a config might rely on each other, this
    function keeps trying to promote things until everything makes sense. This
    is checked by flattening the dictionary first to ensure that if all of the
    innermost values were in the topmost level, everything would be resolved.

    Parameters
    ----------
    config : dict
        The config to search in
    """
    all_keys = list(config)
    needed_promotions = [
        key.replace("promote_", "") for key in all_keys if key.startswith("promote_")
    ]
    if set(needed_promotions).issubset(flatten_bottom_up(config)):
        while needed_promotions:
            current_key_loop = [
                key for key in list(config) if not key.startswith("promote_")
            ]
            for key in current_key_loop:
                promoted_key = promote_value_to_key(config, key)
                if promoted_key:
                    needed_promotions.remove(promoted_key)
    else:
        raise ValueError(
            "This configuration does not have enough information to promote everything!"
        )


def freeze(unhasable):
    """Allows you to hash lists and dicts"""
    if isinstance(unhasable, dict):
        return frozenset((key, freeze(value)) for key, value in unhasable.items())
    if isinstance(unhasable, list):
        return tuple(freeze(value) for value in unhasable)
    return unhasable


def attach_to_config_and_reduce_keyword(config, full_keyword, reduced_keyword):
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
                config[item] = yaml_file_to_dict(loadable_item)
                for attachment in CONFIGS_TO_ALWAYS_ATTACH_AND_REMOVE:
                    attach_to_config_and_remove(config[item], attachment)
    del config[full_keyword]


def recursive_make_choices(config):
    """Recursively calls make choices for any dict in config"""
    all_config_keys = list(config)
    for k in all_config_keys:
        v = config[k]
        if isinstance(k, str) and k.startswith("choose_"):
            make_choice_in_config(config, k.replace("choose_", ""))
        if isinstance(v, dict):
            recursive_make_choices(v)


def recursive_promote_all(config):
    """Recursively calls promote for any dict in config"""
    promote_all(config)
    for key in list(config):
        value = config[key]
        if isinstance(value, dict):
            recursive_promote_all(value)


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
                this_thing["inherited_attrs"][k] = v  # if k not in config[key]
                this_thing[k] = v  # PG: I'm not 100% sure here, but it seems to work?
            else:
                logging.debug("%s already has an attribute %s", thing_below, k)
                this_thing["progenitor_attrs"][k] = [v]
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
    all_computers = yaml_file_to_dict("all_machines.yaml")
    for this_computer in all_computers:
        for computer_pattern in all_computers[this_computer].values():
            if re.match(computer_pattern, socket.gethostname()):
                return this_computer + ".yaml"
    raise FileNotFoundError(
        "The yaml file for this computer (%s) could not be determined!"
        % socket.gethostname()
    )


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
        if self.config["standalone_model"]:
            self.config = {
                **setup_relevant_configs,
                **ConfigComponent(self.config["model"]),
            }
            recursive_make_choices(self.config)
            print("Unordered DICT, try again!")
            # Since the dictionary resolves choices in an unordered way, there
            # might still be unresolved choices.
            #
            # To resolve, do the pass down again:
            pass_down(self.config, "submodels")
            # And re-resolve choices:
            recursive_make_choices(self.config)
        else:
            attach_to_config_and_reduce_keyword(self.config, "include_models", "models")
            for model in self.config["models"]:
                self.config[model] = ConfigComponent(model)


class ConfigComponent(GeneralConfig):
    """ Config class for components """

    def _config_init(self):
        attach_to_config_and_reduce_keyword(
            self.config, "include_submodels", "submodels"
        )
        pass_down(self.config, "submodels")
        recursive_make_choices(self.config)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
