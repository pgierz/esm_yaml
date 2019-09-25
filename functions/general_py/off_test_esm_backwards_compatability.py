"""
Tests for the ESM-Config YAML Parser
"""
import os
import unittest

import esm_backwards_compatability


class Test_ShellscriptToUserConfig(unittest.TestCase):
    def test_produces_dictionary(self):
        """Makes sure all the runscript parts get sorted into a user dict"""
        # TODO: Paul really thinks this should be broken down into smaller steps...
        answer = esm_backwards_compatability.ShellscriptToUserConfig("LGM-Control.run")
        expected_answer = {
            "echam": {
                "NMONTH": "0",
                "MODEL_DIR": "/Users/pgierz/esm-master/echam-test",
                "RES": "T63",
                "CLONP": "294.42",
                "SCENARIO": "PALEO",
                "INI_RESTART_DIR": "/work/ab0246/a270064/esm-experiments/lgm_anm/restart/echam",
                "DISTURBANCE": "1.00001",
                "INI_PARENT_EXP_ID": "lgm_anm",
                "DATASET": "r0007",
                "NYEAR": "1",
                "CO2": "190.0e-6",
                "CH4": "0.375e-6",
                "nproca": "12",
                "VLTCLIM": "/work/ab0246/a270064/esm-experiments/lgm_anm/input/echam/T63LGM_VLTCLIM.nc",
                "INITIAL_DATE": "1850-01-01",
                "JAN_SURF": "/work/ab0246/a270064/esm-experiments/lgm_anm/input/echam/T63LGM_jan_surf.nc",
                "VERSION": "test",
                "BIN_DIR": "/Users/pgierz/esm-master/echam-test/bin",
                "CECC": "0.018994",
                "DISTURBED_YEARS": "1894",
                "INI_PARENT_DATE": "37991231",
                "N2O": "0.200e-6",
                "COBLD": "22.949",
                "POOL_DIR": "/pool/data",
                "VGRATCLIM": "/work/ab0246/a270064/esm-experiments/lgm_anm/input/echam/T63LGM_VGRATCLIM.nc",
                "LRESUME": "1",
                "nprocb": "24",
                "FINAL_DATE": "3850-01-01",
            },
            "jsbach": {
                "LAND_BOUNDARY_CONDITIONS": "/work/ab0246/a270064/esm-experiments/lgm_anm/input/jsbach/jsbach_T63LGM_11tiles_5layers_1850.nc",
                "DATASET": "r0009",
                "DYNVEG": "dynveg",
                "INI_RESTART_DIR": "/work/ab0246/a270064/esm-experiments/lgm_anm/restart/jsbach",
            },
            "hdmodel": {
                "INI_RESTART_DIR": "/work/ab0246/a270064/esm-experiments/lgm_anm/restart/hdmodel",
                "HDPARA_FILE": "/work/ab0246/a270064/esm-experiments/lgm_anm/input/hdmodel/hdpara.nc",
            },
            "general": {
                "setup_name": "echam_standalone",
                "ACCOUNT": "ab0246",
                "BASE_DIR": "/work/ba0989/a270077/AWICM_PISM",
                "compute_time": "03:00:00",
                "post_time": "01:00:00",
                "check": "0",
                "remove_post_dir": "1",
            },
        }
        self.assertEqual(answer, expected_answer)


if __name__ == "__main__":
    unittest.main()
