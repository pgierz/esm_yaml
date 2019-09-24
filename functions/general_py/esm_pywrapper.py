#!/usr/bin/env python
"""
A small wrapper that combines the shell interface and the Python interface
"""

# Import from Python Standard Library
import argparse
import logging
import os

# Add external libraries:
import sys

sys.path.append("../external_py/coloredlogs")
sys.path.append("../external_py/f90nml")
sys.path.append("../external_py/humanfriendly")
sys.path.append("../external_py/six")
sys.path.append("../external_py/tqdm")


# The YAML Lib isn't python agnostic
import six

if six.PY2:
    sys.path.append("../external_py/pyyaml/lib")
    sys.path.append("../external_py/pyyaml/lib/yaml")
elif six.PY3:
    sys.path.append("../external_py/pyyaml/lib3")
    sys.path.append("../external_py/pyyaml/lib3/yaml")

# Import from 3rd Party packages
import coloredlogs


# Import from this package
import esm_backwards_compatability
import esm_sim_objects

# Logger and related constants
logger = logging.getLogger("root")
DEBUG_MODE = logger.level == logging.DEBUG
FORMAT = (
    "[%(asctime)s,%(msecs)03d:%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
)
f_handler = logging.FileHandler("file.log")
f_handler.setFormatter(FORMAT)
logger.addHandler(f_handler)


def parse_shargs():
    """ The arg parser for interactive use """
    parser = argparse.ArgumentParser()
    parser.add_argument("runscript", default=None)

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

    parser.add_argument(
        "-e", "--expid", help="The experiment ID to use", default="test"
    )

    parser.add_argument(
        "-c",
        "--check",
        help="Run in check mode (don't submit job to supercomputer)",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "-t",
        "--task",
        help="The task to run. Choose from: compute, post, couple",
        default="compute",
    )

    parser.add_argument("-x", "--exclude", help="e[x]clude this step", default=None)
    parser.add_argument("-o", "--only", help="[o]nly do this step", default=None)
    parser.add_argument(
        "-r", "--resume-from", help="[r]esume from this step", default=None
    )

    # PG: Might not work anymore:
    parser.add_argument(
        "-U",
        "--update",
        help="[U]date the tools from the current version",
        default=None,
    )

    return parser.parse_args()


if __name__ == "__main__":
    ARGS = parse_shargs()
    coloredlogs.install(fmt=FORMAT, level=ARGS.loglevel)

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
