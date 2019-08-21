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
import os
import unittest

from esm_yaml import parser


class Testparser(unittest.TestCase):
    """Tests for the parser module level functions"""

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

        for valid_extension in parser.YAML_AUTO_EXTENSIONS:
            with open("test" + valid_extension, "w") as test_file:
                test_file.write(document)
            result = parser.yaml_file_to_dict("test")
            try:
                self.assertIsInstance(result, dict)
            finally:
                os.remove("test" + valid_extension)
        with open("test.hjkl", "w") as bad_test_file:
            bad_test_file.write(document)
        try:
            self.assertRaises(FileNotFoundError, parser.yaml_file_to_dict, "test")
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
            parser.attach_to_config_and_remove(test_dict, "further_reading")
            self.assertNotIn("further_reading", test_dict)
            self.assertIn("something_more", test_dict)
        finally:
            os.remove("more.yaml")


if __name__ == "__main__":
    unittest.main()
