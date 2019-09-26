"""
Tests for the ESM-Config YAML Parser
"""
import os
import unittest

try:
    import unittest.mock as mock

    mock_avail = True
except ImportError:
    try:
        import mock

        mock_avail = True
    except ImportError:
        mock_avail = False

import esm_parser


class Test_resolve_basic_choose(unittest.TestCase):
    def test_basic_choose_target_in_key(self):
        t_dict_before = {
            "echam": {
                "choose_computer.cores_per_node": {
                    36: {"a": "choice one"},
                    42: {"a": "choice two"},
                }
            },
            "computer": {"cores_per_node": 36},
        }

        t_dict_after = {
            "echam": {"a": "choice one"},
            "computer": {"cores_per_node": 36},
        }
        esm_parser.resolve_basic_choose(
            t_dict_before, t_dict_before["echam"], "choose_computer.cores_per_node"
        )
        self.assertEqual(t_dict_before, t_dict_after)

    def test_dirk_choose(self):
        t_dict_before = {
            "choose_useMPI": {
                "intel": {"a": "choice one"},
                "bull": {"a": "choice two"},
            },
            "useMPI": "intel",
        }

        t_dict_after = {"a": "choice one", "useMPI": "intel"}
        esm_parser.resolve_basic_choose(t_dict_before, t_dict_before, "choose_useMPI")
        self.assertEqual(t_dict_before, t_dict_after)

    def test_add_chapter(self):
        test_dict = {
            "useMPI": "intelmpi",
            "module_actions": ["purge", "load gcc/4.8.2"],
            "choose_useMPI": {"intelmpi": {"add_module_actions": ["unload intelmpi"]}},
        }
        result_dict = {
            "useMPI": "intelmpi",
            "module_actions": ["purge", "load gcc/4.8.2", "unload intelmpi"],
        }
        esm_parser.resolve_basic_choose(test_dict, test_dict, "choose_useMPI")
        print(test_dict)
        self.assertEqual(test_dict, result_dict)


if __name__ == "__main__":
    unittest.main()
