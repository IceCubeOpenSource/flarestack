import numpy as np
from astropy import units as u
from astropy.coordinates import Distance
import datetime
import os
import cPickle as Pickle
from flarestack.core.results import ResultsHandler
from flarestack.data.icecube.ps_tracks.ps_v002_p01 import IC86_1_dict
from flarestack.shared import plot_output_dir, flux_to_k, analysis_dir, \
    catalogue_dir
from flarestack.utils.reference_sensitivity import reference_sensitivity
from flarestack.cluster import run_desy_cluster as rd
from flarestack.core.minimisation import MinimisationHandler
from flarestack.core.injector import Injector
import matplotlib.pyplot as plt
import math
from flarestack.utils.prepare_catalogue import cat_dtype
from flarestack.utils.neutrino_cosmology import ccsn_madau, \
    ccsn_clash_candels, define_cosmology_functions, integrate_over_z, \
    cumulative_z
from scipy.interpolate import interp1d

# Initialise Injectors/LLHs

# Set up what is "injected" into the fake dataset. This is a simulated source

pre_window = 5.

# Use a source that is constant in time

injection_time = {
    "Name": "Steady",
    "Pre-Window": pre_window,
    "Post-Window": 0
}

# Use a source with a spectral index of -2, with an energy range between
# 100 GeV and 10 Pev (10**7 GeV).

injection_gamma = 2.0

injection_energy = {
    "Name": "Power Law",
    "Gamma": injection_gamma,
    "E Min": 10 ** 2,
    "E Max": 10 ** 7
}

# Fix injection time/energy PDFs, and use "Poisson Smearing" to simulate
# random variations in detected neutrino numbers

inj_kwargs = {
    "Injection Energy PDF": injection_energy,
    "Injection Time PDF": injection_time,
    "Poisson Smear?": True,
}

inj = Injector(IC86_1_dict, [], **inj_kwargs)

season_start = inj.time_pdf.t0
season_end = inj.time_pdf.t1

# The CCSN rate from Madau will be used. We assume here a neutrino-bright
# fraction of 1.0 (i.e we assume that all CCSN are neutrino sources)


rate = ccsn_clash_candels

rate_per_z, nu_flux_per_z, cumulative_nu_flux = define_cosmology_functions(
    rate, 1 * u.erg, injection_gamma, nu_bright_fraction=1.0
)

print "We can integrate the CCSN rate up to z=8.0. This gives",
n_tot = integrate_over_z(rate_per_z, zmin=0.0, zmax=8.0)
print "{:.3E}".format(n_tot)

local_z = 0.1

print "We will only simulate up to z=" + str(local_z) + ".",
n_local = integrate_over_z(rate_per_z, zmin=0.0, zmax=local_z)
print "In this volume, there are", "{:.3E}".format(n_local)

sim_length = 1 * u.year

print "We simulate for", sim_length

n_local = int(n_local * sim_length * 0.5)

print "We will simulate only the northern sky. This leaves", n_local

print "Entries in catalogue", n_local

print "We expect this region to contribute",
print "{:.3g}".format(
    cumulative_nu_flux(local_z)[-1]/cumulative_nu_flux(8.0)[-1]),
print "of all the flux from this source class"

n_catalogue = np.logspace(-3, 0, 17) * n_local

cat_names = [catalogue_dir + "random/" + str(int(n)) + "_cat.npy"
             for n in n_catalogue]


def make_random_catalogue():
    catalogue = np.empty(n_local, dtype=cat_dtype)

    catalogue["Name"] = ["src" + str(i) for i in range(n_local)]
    catalogue["ra"] = np.random.uniform(0., 2 * np.pi, n_local)
    catalogue["dec"] = np.arcsin(np.random.uniform(0, 1, n_local))
    catalogue["Relative Injection Weight"] = np.ones(n_local)
    catalogue["Ref Time (MJD)"] = np.random.uniform(
        season_start + pre_window, season_end, n_local
    )

    # Define conversion fraction to sample redshift distribution

    zrange = np.linspace(0, local_z, 1e3)

    count_ints = [(x * sim_length).value for x in cumulative_z(rate_per_z, zrange)]
    count_ints = np.array([0] + count_ints)/max(count_ints)

    rand_to_z = interp1d(count_ints, zrange[:-1])

    z_vals = sorted(rand_to_z(np.random.uniform(0., 1.0, n_local)))

    mpc_vals = [Distance(z=z).to("Mpc").value for z in z_vals]

    catalogue["Distance (Mpc)"] = np.array(mpc_vals)

    for i, n in enumerate(n_catalogue):

        index = int(n)

        cat = catalogue[:index]

        cat_path = cat_names[i]

        try:
            os.makedirs(os.path.dirname(cat_path))
        except OSError:
            pass
        np.save(cat_path, cat)

        print "Saved", cat_path


if __name__ == "__main__":
    make_random_catalogue()

if np.sum([os.path.isfile(x) for x in cat_names]) < len(cat_names):
    make_random_catalogue()

