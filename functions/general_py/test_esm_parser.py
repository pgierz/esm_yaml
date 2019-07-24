import unittest
import logging
import coloredlogs

FORMAT = (
    "[%(asctime)s,%(msecs)03d:%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
)

coloredlogs.install(fmt=FORMAT, level=logging.DEBUG)


import esm_parser


class TestParserFuncs(unittest.TestCase):
    def test_make_choices(self):
        input_dict = {
            "hostnames": {
                "login": "ollie[01]",
                "compute": "prod-[0-9]{3}",
                "mini": "mini",
            },
            "nodetypes": ["login", "compute", "fat", "mini"],
            "batch_system": "slurm",
            "operating_system": {"linux": "centos"},
            "jobtype": "compute",
            "choose_jobtype": {
                "post": {"partition": "smp"},
                "compute": {"partition": "mpp"},
            },
            "choose_partition": {
                "mpp": {"cores_per_node": 36},
                "smp": {"cores_per_node": 1},
            },
            "logical_cpus_per_core": 1,
            "threads_per_core": 1,
            "pool_directories": {
                "pool": "/work/ollie/pool",
                "projects": "/work/ollie/projects",
            },
            "cores_per_node": 888,
            "choose_submitted": {True: {"modules_needed": ["centoslibs"]}},
            "submitted": True,
            "accounting": False,
            "hyper_flag": "",
        }

        output_dict = {
            "hostnames": {
                "login": "ollie[01]",
                "compute": "prod-[0-9]{3}",
                "mini": "mini",
            },
            "nodetypes": ["login", "compute", "fat", "mini"],
            "batch_system": "slurm",
            "operating_system": {"linux": "centos"},
            "jobtype": "compute",
            "partition": "mpp",
            "cores_per_node": 36,
            "logical_cpus_per_core": 1,
            "threads_per_core": 1,
            "pool_directories": {
                "pool": "/work/ollie/pool",
                "projects": "/work/ollie/projects",
            },
            "modules_needed": ["centoslibs"],
            "submitted": True,
            "accounting": False,
            "hyper_flag": "",
        }

        answer = esm_parser.make_choices_new(
            ["computer"],
            input_dict,
            {"model": "some_model", "setup": "some_setup", "computer": input_dict},
        )
        print(answer)
        self.assertEqual(output_dict, answer)

    def test_make_choices_nested(self):
        input_dict = {
            "model": "some_model",
            "setup": "some_setup",
            "computer": {
                "hostnames": {
                    "login": "ollie[01]",
                    "compute": "prod-[0-9]{3}",
                    "mini": "mini",
                },
                "nodetypes": ["login", "compute", "fat", "mini"],
                "batch_system": "slurm",
                "operating_system": {"linux": "centos"},
                "jobtype": "compute",
                "choose_jobtype": {
                    "post": {"partition": "smp"},
                    "compute": {"partition": "mpp"},
                },
                "choose_partition": {
                    "mpp": {"cores_per_node": 36},
                    "smp": {"cores_per_node": 1},
                },
                "logical_cpus_per_core": 1,
                "threads_per_core": 1,
                "pool_directories": {
                    "pool": "/work/ollie/pool",
                    "projects": "/work/ollie/projects",
                },
                "cores_per_node": 888,
                "choose_submitted": {True: {"modules_needed": ["centoslibs"]}},
                "submitted": True,
                "accounting": False,
                "hyper_flag": "",
            },
            "doodad": {"choose_cores_per_node": {"36": {"thing"}}},
        }

        output_dict = {
            "model": "some_model",
            "setup": "some_setup",
            "computer": {
                "hostnames": {
                    "login": "ollie[01]",
                    "compute": "prod-[0-9]{3}",
                    "mini": "mini",
                },
                "nodetypes": ["login", "compute", "fat", "mini"],
                "batch_system": "slurm",
                "operating_system": {"linux": "centos"},
                "jobtype": "compute",
                "partition": "mpp",
                "cores_per_node": 36,
                "logical_cpus_per_core": 1,
                "threads_per_core": 1,
                "pool_directories": {
                    "pool": "/work/ollie/pool",
                    "projects": "/work/ollie/projects",
                },
                "modules_needed": ["centoslibs"],
                "submitted": True,
                "accounting": False,
                "hyper_flag": "",
            },
            "doodad": "thing",
        }

        answer = esm_parser.make_choices_new(["computer"], input_dict, input_dict)
        self.maxDiff = None
        self.assertEqual(output_dict, answer)


if __name__ == "__main__":
    unittest.main()
