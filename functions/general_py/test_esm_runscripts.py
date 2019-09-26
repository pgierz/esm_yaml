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
from esm_calendar import Date


class Test_module_constants(unittest.TestCase):
    def test_constant_types(self):
        self.assertIsInstance(esm_parser.DATE_MARKER, str)
        self.assertIsInstance(esm_parser.FUNCTION_PATH, str)


class Test_yaml_file_to_dict(unittest.TestCase):
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
            self.assertRaises(Exception, esm_parser.yaml_file_to_dict, "test")
        finally:
            os.remove("test.hjkl")


class Test_attach_to_config_and_remove(unittest.TestCase):
    def setUp(self):
        self.config = {}

    def test_skips_loop_if_attach_key_missing(self):
        """Makes sure the loop is skipped if the attach_key is missing"""
        attach_key = "some_key_not_in_dummy_config"
        self.assertIs(
            None, esm_parser.attach_to_config_and_remove(self.config, attach_key)
        )

    def test_attach_value_is_badtype(self):
        """Makes sure a type error is raised if anything not a list or str is passed"""
        for attach_key in [1, 1.0]:
            self.config[attach_key] = attach_key
            self.assertRaises(
                TypeError,
                esm_parser.attach_to_config_and_remove,
                self.config,
                attach_key,
            )


def replace_with_str_recursive_func(tree, right, full_config):
    while not tree[-1]:
        tree = tree[:-1]
    if len(tree) > 1:
        type_of_sender = type(esm_parser.recursive_get(full_config, tree))
    else:
        type_of_sender = dict
    if type_of_sender == dict:
        return {tree[-1]: "Went through recursion"}
    return "Went through recursion"


def recursive_always_tester(tree, right, full_config):
    if not tree[-1]:
        tree = tree[:-1]
        type_of_sender = int
    else:
        type_of_sender = dict
    if type_of_sender == dict:
        return {tree[-1]: right}
    else:
        if isinstance(right, list):
            right = right[::-1]
        if isinstance(right, str):
            right = "newstr"
        if isinstance(right, int):
            right = right + 1
    return right


class Test_recursive_run_function(unittest.TestCase):
    def test_mappings(self):
        tree = []
        test_dict = {"echam": {1: 1, 2: [1, 2]}, "general": {"d": 1}}
        esm_parser.recursive_run_function(
            tree, test_dict, "mappings", replace_with_str_recursive_func, test_dict
        )
        r_dict = {
            "echam": "Went through recursion",
            "general": "Went through recursion",
        }
        self.assertEqual(r_dict, test_dict)

    def test_atomic(self):
        tree = []
        test_dict = {"echam": {1: 1, 2: [1, [1, 2]]}, "general": {"d": 1}}
        esm_parser.recursive_run_function(
            tree, test_dict, "atomic", replace_with_str_recursive_func, test_dict
        )
        r_dict = {
            "echam": {
                1: "Went through recursion",
                2: [
                    "Went through recursion",
                    ["Went through recursion", "Went through recursion"],
                ],
            },
            "general": {"d": "Went through recursion"},
        }
        self.assertEqual(r_dict, test_dict)

    def test_always(self):
        tree = []
        test_dict = {"echam": {"a": 1, "b": [1, 2, "str"]}, "general": {"d": 1}}
        esm_parser.recursive_run_function(
            tree, test_dict, "always", recursive_always_tester, test_dict
        )
        r_dict = {"echam": {"a": 2, "b": ["newstr", 3, 2]}, "general": {"d": 2}}
        self.assertEqual(r_dict, test_dict)


class Test_find_variable(unittest.TestCase):
    def test_finds_answer_with_sensible_input(self):
        tdict = {"echam": {"resolution": "T63"}}
        r = esm_parser.find_variable(
            ["echam", "something", "lala"],
            "${echam.resolution}",
            tdict,
            esm_parser.gray_list,
            isblacklist=True,
        )
        self.assertEqual(r, "T63")

    def test_finds_answer_in_general_blacklist_off(self):
        tdict = {"echam": {"resolution": "T63"}, "general": {"lresume": True}}
        r = esm_parser.find_variable(
            ["echam", "something", "lala"],
            "${lresume}",
            tdict,
            esm_parser.gray_list,
            isblacklist=False,
        )
        self.assertEqual(r, "True")

    def test_leaves_answer_blacklist_off(self):
        tdict = {"echam": {"resolution": "T63"}, "general": {"lresume": True}}
        r = esm_parser.find_variable(
            ["echam", "something", "lala"],
            "${lresume}",
            tdict,
            esm_parser.gray_list,
            isblacklist=True,
        )
        self.assertEqual(r, "${lresume}")


class Test_actually_find_variable(unittest.TestCase):
    def test_finds_answer_with_sensible_input(self):
        tdict = {"echam": {"resolution": "T63"}}
        r = esm_parser.actually_find_variable(
            ["echam", "something", "lala"], "echam.resolution", tdict
        )
        self.assertEqual(r, "T63")

    def test_finds_answer_in_general(self):
        tdict = {"echam": {"resolution": "T63"}, "general": {"lresume": True}}
        r = esm_parser.actually_find_variable(
            ["echam", "something", "lala"], "lresume", tdict
        )
        self.assertEqual(r, True)

    def test_raises_error_without_answer(self):
        tdict = {"echam": {"resolution": "T63"}}
        self.assertRaises(
            ValueError,
            esm_parser.actually_find_variable,
            ["echam", "something", "lala"],
            "echam.nonsense",
            tdict,
        )


class Test_list_to_multikey(unittest.TestCase):
    def test_skips_func_if_bad_tree(self):
        r = esm_parser.list_to_multikey(
            [None], "something", {"config": "lala"}, [], False
        )
        self.assertEqual(r, "something")

    def test_skips_first_block_if_lhs_isnt_str(self):
        r = esm_parser.list_to_multikey(
            ["computer", "ncores", 63], 63, {"computer": {"ncores": 63}}, [], False
        )
        self.assertEqual(r, 63)

    def test_lhs_str_and_rhs_str(self):
        tdict = {
            "echam": {
                "[[streams-->STREAM]]": "restart_${expid}_STREAM.nc",
                "streams": ["echam", "accw", "co2"],
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", "[[streams-->STREAM]]"],
            "restart_${expid}_STREAM.nc",
            tdict,
            [],
            False,
        )
        self.assertEqual(
            r,
            {
                "echam": "restart_${expid}_echam.nc",
                "accw": "restart_${expid}_accw.nc",
                "co2": "restart_${expid}_co2.nc",
            },
        )

    def test_lhs_str_and_rhs_list(self):
        tdict = {
            "echam": {
                "[[streams-->STREAM]]": [
                    "restart_one_${expid}_STREAM.nc",
                    "restart_two_${expid}_STREAM.nc",
                ],
                "streams": ["echam", "accw", "co2"],
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", "[[streams-->STREAM]]"],
            ["restart_one_${expid}_STREAM.nc", "restart_two_${expid}_STREAM.nc"],
            tdict,
            [],
            False,
        )
        expected_answer = {
            "echam": [
                "restart_one_${expid}_echam.nc",
                "restart_one_${expid}_accw.nc",
                "restart_one_${expid}_co2.nc",
                "restart_two_${expid}_echam.nc",
                "restart_two_${expid}_accw.nc",
                "restart_two_${expid}_co2.nc",
            ],
            "accw": [
                "restart_one_${expid}_echam.nc",
                "restart_one_${expid}_accw.nc",
                "restart_one_${expid}_co2.nc",
                "restart_two_${expid}_echam.nc",
                "restart_two_${expid}_accw.nc",
                "restart_two_${expid}_co2.nc",
            ],
            "co2": [
                "restart_one_${expid}_echam.nc",
                "restart_one_${expid}_accw.nc",
                "restart_one_${expid}_co2.nc",
                "restart_two_${expid}_echam.nc",
                "restart_two_${expid}_accw.nc",
                "restart_two_${expid}_co2.nc",
            ],
        }
        self.assertEqual(r, expected_answer)

    def test_lhs_str_and_rhs_list_nostr_rhs(self):
        tdict = {
            "echam": {
                "[[streams-->STREAM]]": [True, 1],
                "streams": ["echam", "accw", "co2"],
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", "[[streams-->STREAM]]"], [True, 1], tdict, [], False
        )
        expected_answer = {"echam": [True, 1], "accw": [True, 1], "co2": [True, 1]}
        self.assertEqual(r, expected_answer)

    def test_double_list(self):
        tdict = {
            "echam": {
                "[[streams-->STREAM]]_[[streams-->OTHER]]": "f_STREAM_OTHER.nc",
                "streams": ["echam", "accw", "co2"],
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", "[[streams-->STREAM]]_[[streams-->OTHER]]"],
            "f_STREAM_OTHER.nc",
            tdict,
            [],
            False,
        )
        # Expected answer in pretty format:
        # accw_accw: f_accw_accw.nc
        # accw_co2: f_accw_co2.nc
        # accw_echam: f_accw_echam.nc
        # co2_accw: f_co2_accw.nc
        # co2_co2: f_co2_co2.nc
        # co2_echam: f_co2_echam.nc
        # echam_accw: f_echam_accw.nc
        # echam_co2: f_echam_co2.nc
        # echam_echam: f_echam_echam.nc
        expected_answer = {
            "echam_echam": "f_echam_echam.nc",
            "echam_accw": "f_echam_accw.nc",
            "echam_co2": "f_echam_co2.nc",
            "accw_echam": "f_accw_echam.nc",
            "accw_accw": "f_accw_accw.nc",
            "accw_co2": "f_accw_co2.nc",
            "co2_echam": "f_co2_echam.nc",
            "co2_accw": "f_co2_accw.nc",
            "co2_co2": "f_co2_co2.nc",
        }
        self.assertEqual(r, expected_answer)

    def test_lhs_no_fence(self):
        tdict = {"echam": {"42": "rhs for 42"}}
        r = esm_parser.list_to_multikey(["echam", "42"], "rhs for 42", tdict, [], False)
        self.assertEqual(r, {"42": "rhs for 42"})

    def test_rhs_str_and_rhs_list_fence(self):
        tdict = {
            "echam": {
                "streams": ["a", "b", "c"],
                "files_with_streams": "file_[[streams-->STREAM]].nc",
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", True], "file_[[streams-->STREAM]].nc", tdict, [], False
        )
        expected_answer = ["file_a.nc", "file_b.nc", "file_c.nc"]
        self.assertEqual(expected_answer, r)

    def test_rhs_str_and_rhs_list_fence_double_list(self):
        tdict = {
            "echam": {
                "streams": ["a", "b", "c"],
                "files_with_streams": "file_[[streams-->STREAM]][[streams-->OTHER]].nc",
            }
        }
        r = esm_parser.list_to_multikey(
            ["echam", True],
            "file_[[streams-->STREAM]][[streams-->OTHER]].nc",
            tdict,
            [],
            False,
        )
        expected_answer = [
            "file_aa.nc",
            "file_ab.nc",
            "file_ac.nc",
            "file_ba.nc",
            "file_bb.nc",
            "file_bc.nc",
            "file_ca.nc",
            "file_cb.nc",
            "file_cc.nc",
        ]
        self.assertEqual(expected_answer, r)

    def test_rhs_not_str(self):
        tdict = {"echam": {42: 42}}
        r = esm_parser.list_to_multikey(["echam", 42], 42, tdict, [], False)
        self.assertEqual(r, 42)

    def test_lhs_bool(self):
        tdict = {"echam": {"forcing": {True: "lala"}}}
        r = esm_parser.list_to_multikey(
            ["echam", "forcing", True], "lala", tdict, [], False
        )
        self.assertEqual(r, {True: "lala"})


class Test_determine_computer_from_hostname(unittest.TestCase):
    def test_loads_generic(self):
        if not mock_avail:
            self.skipTest()
        with mock.patch("socket.gethostname", return_value="uss_enterprise"):
            machine_config = esm_parser.determine_computer_from_hostname()
            self.assertEqual(
                machine_config, esm_parser.FUNCTION_PATH + "/machines/generic.yaml"
            )

    def test_loads_mistral(self):
        if not mock_avail:
            self.skipTest()
        with mock.patch("socket.gethostname", return_value="mlogin105"):
            machine_config = esm_parser.determine_computer_from_hostname()
            self.assertEqual(
                machine_config, esm_parser.FUNCTION_PATH + "/machines/mistral.yaml"
            )

    def test_loads_ollie(self):
        if not mock_avail:
            self.skipTest()
        with mock.patch("socket.gethostname", return_value="ollie0"):
            machine_config = esm_parser.determine_computer_from_hostname()
            self.assertEqual(
                machine_config, esm_parser.FUNCTION_PATH + "/machines/ollie.yaml"
            )


class Test_do_math_in_entry(unittest.TestCase):
    def setUp(self):
        self.math_test_dict = {
            "skip_var": "${something}",
            "simple_math_add": "$((1+2))",
            "spaced_math_add": "$(( 1 + 2 ))",
            "simple_math_sub": "$((1-2))",
            "spaced_math_sub": "$(( 1 - 2 ))",
            "date_math_add": "$(( 18500101"
            + esm_parser.DATE_MARKER
            + " + 00010000"
            + esm_parser.DATE_MARKER
            + "))",
        }

    def test_skips_vars(self):
        new_entry = esm_parser.do_math_in_entry(
            ["skip_var", None], self.math_test_dict["skip_var"], self.math_test_dict
        )
        self.assertEqual(new_entry, self.math_test_dict["skip_var"])
        self.assertNotEqual(new_entry, "lalalal")
        self.assertNotEqual(new_entry, 1234)

    def test_simple_math_add(self):
        new_entry = esm_parser.do_math_in_entry(
            ["simple_math_add", None],
            self.math_test_dict["simple_math_add"],
            self.math_test_dict,
        )
        self.assertEqual("3", new_entry)

    def test_spaced_math_add(self):
        new_entry = esm_parser.do_math_in_entry(
            ["spaced_math_add", None],
            self.math_test_dict["spaced_math_add"],
            self.math_test_dict,
        )
        self.assertEqual("3", new_entry)

    def test_date_math_add(self):
        new_entry = esm_parser.do_math_in_entry(
            ["date_math_add", None],
            self.math_test_dict["date_math_add"],
            self.math_test_dict,
        )
        self.assertEqual(str(Date.from_list([1851, 1, 1, 0, 0, 0])), new_entry)

    def test_simple_math_sub(self):
        new_entry = esm_parser.do_math_in_entry(
            ["simple_math_sub", None],
            self.math_test_dict["simple_math_sub"],
            self.math_test_dict,
        )
        self.assertEqual("-1", new_entry)

    def test_spaced_math_sub(self):
        new_entry = esm_parser.do_math_in_entry(
            ["spaced_math_sub", None],
            self.math_test_dict["spaced_math_sub"],
            self.math_test_dict,
        )
        self.assertEqual("-1", new_entry)

    def test_spaced_math_sub(self):
        new_entry = esm_parser.do_math_in_entry(
            ["spaced_math_sub", None],
            self.math_test_dict["spaced_math_sub"],
            self.math_test_dict,
        )
        self.assertEqual("-1", new_entry)


class Test_mark_dates(unittest.TestCase):
    def setUp(self):
        self.date_test_dict = {
            "skip_var": "${something.something}",
            "marked_date": "a_thing",
        }

    def test_skips_vars(self):
        new_rhs = esm_parser.mark_dates(
            ["skip_var"], self.date_test_dict["skip_var"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_var"])

    def test_marks_dates(self):
        new_rhs = esm_parser.mark_dates(["marked_date"], "a_thing", self.date_test_dict)
        self.assertEqual(new_rhs, "a_thing" + esm_parser.DATE_MARKER)

    def test_skips_tree(self):
        new_rhs = esm_parser.mark_dates(
            ["marked_date", None], "a_thing", self.date_test_dict
        )
        self.assertEqual(new_rhs, "a_thing" + esm_parser.DATE_MARKER)


class Test_unmark_dates(unittest.TestCase):
    def setUp(self):
        self.date_test_dict = {
            "skip_var": "${something.something}",
            "marked_date": "a_thing" + esm_parser.DATE_MARKER,
        }

    def test_skips_vars(self):
        new_rhs = esm_parser.unmark_dates(
            ["skip_var"], self.date_test_dict["skip_var"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_var"])

    def test_unmarks_dates(self):
        new_rhs = esm_parser.unmark_dates(
            ["marked_date"], self.date_test_dict["marked_date"], self.date_test_dict
        )
        self.assertEqual(new_rhs, "a_thing")

    def test_skips_tree(self):
        new_rhs = esm_parser.unmark_dates(
            ["marked_date", None],
            self.date_test_dict["marked_date"],
            self.date_test_dict,
        )
        self.assertEqual(new_rhs, "a_thing")


class Test_marked_date_to_date_object(unittest.TestCase):
    def setUp(self):
        self.date_test_dict = {
            "skip_var": "${something.something}",
            "skip_date": Date.fromlist([1850, 1, 1, 0, 0, 0]),
            "create_date": "18500101" + esm_parser.DATE_MARKER,
            "just_year_date": "18500101!year" + esm_parser.DATE_MARKER,
            "yearmonth_date": "18500101!syear!smonth" + esm_parser.DATE_MARKER,
            "return_num": 1,
            "return_bool": True,
        }

    def test_skip_vars(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["skip_var"], self.date_test_dict["skip_var"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_var"])

    def test_skip_date(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["skip_date"], self.date_test_dict["skip_date"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_date"])

    def test_skip_tree(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["skip_var", None], self.date_test_dict["skip_var"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_var"])

        new_rhs = esm_parser.marked_date_to_date_object(
            ["skip_date", None], self.date_test_dict["skip_date"], self.date_test_dict
        )
        self.assertEqual(new_rhs, self.date_test_dict["skip_date"])

    def test_create_dates(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["create_date", None],
            self.date_test_dict["create_date"],
            self.date_test_dict,
        )
        self.assertEqual(new_rhs, "18500101")

    def test_create_dates_just_year(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["just_year_date", None],
            self.date_test_dict["just_year_date"],
            self.date_test_dict,
        )
        self.assertEqual(new_rhs, "1850")

    def test_create_dates_yearmonth(self):
        new_rhs = esm_parser.marked_date_to_date_object(
            ["yearmonth_date", None],
            self.date_test_dict["yearmonth_date"],
            self.date_test_dict,
        )
        self.assertEqual(new_rhs, "185001")

    def test_return_other_types(self):
        for return_type in ["return_num", "return_bool"]:
            new_rhs = esm_parser.marked_date_to_date_object(
                [return_type, None],
                self.date_test_dict[return_type],
                self.date_test_dict,
            )
            self.assertEqual(new_rhs, self.date_test_dict[return_type])


class OtherCrap:
    def test_attach_to_config_and_reduce_keyword_typeerror(self):
        config = {"model": "Earth", "include_files": "satellites"}
        config_to_write_to = {}
        full_keyword = "include_files"

        self.assertRaises(
            TypeError,
            esm_parser.attach_to_config_and_reduce_keyword,
            config,
            config_to_write_to,
            full_keyword,
        )


class Junk_I_do_not_understand(object):
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
