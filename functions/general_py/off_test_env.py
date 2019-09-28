#!/usr/bin/env python
import esm_parser
import esm_environment

env = esm_environment.environment_infos()

esm_parser.pprint_config(env)
