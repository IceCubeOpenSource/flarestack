"""A standard time-integrated analysis is performed, using one year of
IceCube data (IC86_1).
"""
from __future__ import print_function
import unittest
import numpy as np
from flarestack.data.icecube.ps_tracks.ps_v002_p01 import IC86_1_dict
from flarestack.utils.prepare_catalogue import ps_catalogue_name
from flarestack.core.unblinding import create_unblinder

# Initialise Injectors/LLHs

llh_dict = {
    "name": "standard",
    "llh_time_pdf": {
        "time_pdf_name": "Steady"
    },
    "llh_energy_pdf": {
        "energy_pdf_name": "PowerLaw"
    }
}

name = "tests/test_likelihood_spatial/"

# Loop over sin(dec) values

sindecs = np.linspace(0.5, -0.5, 3)


# These results arise from high-statistics sensitivity calculations,
# and can be considered the "true" answers. The results we obtain will be
# compared to these values.

true_parameters = [
    [3.195848944038912, 4.0],
    [0.0, 2.9791427015687857],
    [2.39885884692988, 2.800136674169254]
]


class TestTimeIntegrated(unittest.TestCase):

    def setUp(self):
        pass

    def test_declination_sensitivity(self):

        print("\n")
        print("\n")
        print("Testing standard LLH class")
        print("\n")
        print("\n")

        # Test three declinations

        for j, sindec in enumerate(sindecs):
            subname = name + "/sindec=" + '{0:.2f}'.format(sindec) + "/"

            unblind_dict = {
                "name": subname,
                "mh_name": "fixed_weights",
                "datasets": [IC86_1_dict],
                "catalogue": ps_catalogue_name(sindec),
                "llh_dict": llh_dict,
            }

            ub = create_unblinder(unblind_dict)
            key = [x for x in ub.res_dict.keys() if x != "TS"][0]
            res = ub.res_dict[key]
            self.assertEqual(list(res["x"]), true_parameters[j])

            print("Best fit values", list(res["x"]))
            print("Reference best fit", true_parameters[j])


if __name__ == '__main__':
    unittest.main()
