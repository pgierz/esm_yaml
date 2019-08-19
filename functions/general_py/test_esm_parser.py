"""
Tests for the ESM-Config YAML Parser
"""
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import open
from future import standard_library

standard_library.install_aliases()

import logging
import os
import unittest

import esm_parser


class TestParserFuncs(unittest.TestCase):
    def test_yaml_file_to_dict(self):
        """Tests extension expansion and loading of YAML documents"""
        document = """
        model: PISM
        nest:
            Domains:
                - nhem
                - shem
                - gris
                - something
            Resolutions:
                - big
                - small
        """

        for valid_extension in esm_parser.YAML_AUTO_EXTENSIONS:
            with open("test" + valid_extension, "w") as test_file:
                test_file.write(document)
            result = esm_parser.yaml_file_to_dict("test")
            try:
                self.assertIsInstance(result, dict)
            finally:
                os.remove("test" + valid_extension)
        with open("test.hjkl", "w") as bad_test_file:
            bad_test_file.write(document)
        try:
            self.assertRaises(FileNotFoundError, esm_parser.yaml_file_to_dict, "test")
        finally:
            os.remove("test.hjkl")

    def test_attach_to_config_and_remove(self):
        test_dict = {"further_reading": "more"}
        document = """
        something_more:
            - lala
            - tutu
            - tata
        """
        with open("more.yaml", "w") as further_reading:
            further_reading.write(document)
        try:
            esm_parser.attach_to_config_and_remove(test_dict, "further_reading")
            self.assertNotIn("further_reading", test_dict)
            self.assertIn("something_more", test_dict)
        finally:
            os.remove("more.yaml")

    def test_attach_to_config_and_reduce_keyword_typeerror(self):
        config_to_read_from = {"model": "Earth", "include_files": "satellites"}
        config_to_write_to = {}
        full_keyword = "include_files"

        self.assertRaises(
            TypeError,
            esm_parser.attach_to_config_and_reduce_keyword,
            config_to_read_from,
            config_to_write_to,
            full_keyword,
        )

    def test_attach_to_config_and_reduce_keyword_nolevel(self):
        config_to_read_from = {
            "model": "Earth",
            "added_stuff": ["test_echam.satellites"],
        }
        config_to_write_to = {}
        full_keyword = "added_stuff"

        echam_satellites = """
        model: Luna
        description: 'The Moon'
        """
        with open(
            esm_parser.FUNCTION_PATH + "/test_echam/test_echam.satellites.yaml", "w"
        ) as test_yaml:
            test_yaml.write(echam_satellites)

        try:
            esm_parser.attach_to_config_and_reduce_keyword(
                config_to_read_from,
                config_to_write_to,
                full_keyword,
                reduced_keyword="files",
            )
            expected_answer = {
                "files": ["test_echam.satellites"],
                "Luna": {"model": "Luna", "description": "The Moon"},
            }
            self.assertEqual(config_to_write_to, expected_answer)
        finally:
            os.remove(
                esm_parser.FUNCTION_PATH + "/test_echam/test_echam.satellites.yaml"
            )

    def test_attach_to_config_and_reduce_keyword_level(self):
        config_to_read_from = {
            "model": "Earth",
            "added_stuff": ["test_echam.satellites"],
        }
        config_to_write_to = {"levelA": {}}
        full_keyword = "added_stuff"

        echam_satellites = """
        model: Luna
        description: 'The Moon'
        """
        with open(
            esm_parser.FUNCTION_PATH + "/test_echam/test_echam.satellites.yaml", "w"
        ) as test_yaml:
            test_yaml.write(echam_satellites)

        try:
            esm_parser.attach_to_config_and_reduce_keyword(
                config_to_read_from,
                config_to_write_to,
                full_keyword,
                reduced_keyword="files",
                level_to_write_to="levelA",
            )
            expected_answer = {
                "levelA": {"files": ["test_echam.satellites"]},
                "Luna": {"model": "Luna", "description": "The Moon"},
            }
            self.assertEqual(config_to_write_to, expected_answer)
        finally:
            os.remove(
                esm_parser.FUNCTION_PATH + "/test_echam/test_echam.satellites.yaml"
            )

    def test_attach_to_config_and_remove_list(self):
        document = """
        further_reading:
            - test_echam.some_file
        """
        some_file = """
        stuff: things
        """
        try:
            for f, c in zip(
                [
                    "../test_echam/example_test_echam.yaml",
                    "../test_echam/test_echam.some_file.yaml",
                ],
                [document, some_file],
            ):
                with open(f, "w") as test_file:
                    test_file.write(c)
            config = esm_parser.yaml_file_to_dict(
                "../test_echam/example_test_echam.yaml"
            )
            esm_parser.attach_to_config_and_remove(config, "further_reading")
            expected_answer = {"stuff": "things"}
            self.assertEqual(config, expected_answer)
        finally:
            for f in [
                "../test_echam/example_test_echam.yaml",
                "../test_echam/test_echam.some_file.yaml",
            ]:
                os.remove(f)

    def test_attach_to_config_and_remove_simple(self):
        document = """
        further_reading: test_echam.some_file
        """
        some_file = """
        stuff: things
        """
        try:
            for f, c in zip(
                [
                    "../test_echam/example_test_echam.yaml",
                    "../test_echam/test_echam.some_file.yaml",
                ],
                [document, some_file],
            ):
                with open(f, "w") as test_file:
                    test_file.write(c)
            config = esm_parser.yaml_file_to_dict(
                "../test_echam/example_test_echam.yaml"
            )
            esm_parser.attach_to_config_and_remove(config, "further_reading")
            expected_answer = {"stuff": "things"}
            self.assertEqual(config, expected_answer)
        finally:
            for f in [
                "../test_echam/example_test_echam.yaml",
                "../test_echam/test_echam.some_file.yaml",
            ]:
                os.remove(f)


if __name__ == "__main__":
    unittest.main()
