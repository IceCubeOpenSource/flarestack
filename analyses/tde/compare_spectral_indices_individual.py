import numpy as np
import os
import cPickle as Pickle
from core.minimisation import MinimisationHandler
from core.results import ResultsHandler
from data.icecube_pointsource_7_year import ps_7year
from shared import plot_output_dir, flux_to_k, analysis_dir, catalogue_dir
from utils.skylab_reference import skylab_7year_sensitivity
from cluster import run_desy_cluster as rd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from core.time_PDFs import TimePDF

analyses = dict()

# Initialise Injectors/LLHs

# Shared

llh_energy = {
    "Name": "Power Law",
    "Gamma": 2.0,
}

llh_time = {
    "Name": "FixedEndBox"
}

# Standard Time Integration

standard_inj_time = llh_time

standard_inj_kwargs = {
    "Injection Time PDF": standard_inj_time,
    "Injection Energy PDF": llh_energy,
    "Poisson Smear?": True
}

standard_llh = {
    "LLH Energy PDF": llh_energy,
    "LLH Time PDF": llh_time,
    "Fit Gamma?": True,
    "Fit Negative n_s?": True,
    "Fit Weights?": False
}

# Murase model with One day Injection

murase_flare_llh = {
    "LLH Energy PDF": llh_energy,
    "LLH Time PDF": llh_time,
    "Fit Gamma?": True,
    "Fit Negative n_s?": False,
    "Flare Search?": True
}

inj_time_murase = {
    "Name": "Box",
    "Pre-Window": 0,
    "Post-Window": 2.3
}

murase_flare_inj_kwargs = {
    "Injection Time PDF": inj_time_murase,
    "Injection Energy PDF": llh_energy,
    "Poisson Smear?": True
}

# Winter Model with 10 day Injection

winter_energy_pdf = {
    "Name": "Power Law",
    "Gamma": 2.0
}

winter_flare_llh = {
    "LLH Energy PDF": winter_energy_pdf,
    "LLH Time PDF": llh_time,
    "Fit Gamma?": True,
    "Fit Negative n_s?": False,
    "Flare Search?": True
}

winter_flare_inj_time = {
    "Name": "Box",
    "Pre-Window": 0,
    "Post-Window": 10
}

winter_flare_injection_time = {
    "Injection Time PDF": winter_flare_inj_time,
    "Injection Energy PDF": winter_energy_pdf,
    "Poisson Smear?": True,
}

# gammas = [1.8, 1.9, 2.0, 2.1, 2.3, 2.5, 2.7, 2.9]
gammas = [1.8, 2.0, 2.3, 2.5]
# gammas = [2.0, 2.3]
# gammas = [1.99, 2.0, 2.02]
# gammas = [2.5, 2.7, 2.9]

name_root = "analyses/tde/compare_spectral_indices_individual/"

cat_res = dict()

cats = ["Swift J1644+57", "Swift J2058+05"]
# cats = ["jetted"]

for cat in cats:

    name = name_root + cat.replace(" ", "") + "/"

    cat_path = catalogue_dir + "TDEs/individual_TDEs/" + cat + "_catalogue.npy"
    catalogue = np.load(cat_path)

    src_res = dict()

    # lengths = [0.5 * max_window]

    for i, [inj_kwargs, llh_kwargs] in enumerate([
        [standard_inj_kwargs, standard_llh],
        [winter_flare_injection_time, winter_flare_llh],
        [murase_flare_inj_kwargs, murase_flare_llh]
                                    ]):

        label = ["Time-Integrated", "10 Day Flare",
                 "2 Day Flare"][i]
        f_name = ["negative_n_s", "flare_winter", "flare_murase"][i]

        flare_name = name + f_name + "/"

        res = dict()

        for gamma in gammas:

            full_name = flare_name + str(gamma) + "/"

            scale = flux_to_k(skylab_7year_sensitivity(
                np.sin(catalogue["dec"]), gamma=gamma) * 50)

            scale *= 10**i

            inj = dict(inj_kwargs)

            inj["Injection Energy PDF"] = dict(inj["Injection Energy PDF"])

            inj["Injection Energy PDF"]["Gamma"] = gamma

            if "E Min" in inj["Injection Energy PDF"].keys():
                scale *= 10

            mh_dict = {
                "name": full_name,
                "datasets": ps_7year[-3:-1],
                "catalogue": cat_path,
                "inj kwargs": inj,
                "llh kwargs": llh_kwargs,
                "scale": scale,
                "n_trials": 1,
                "n_steps": 10
            }

            # print scale

            analysis_path = analysis_dir + full_name

            try:
                os.makedirs(analysis_path)
            except OSError:
                pass

            pkl_file = analysis_path + "dict.pkl"

            with open(pkl_file, "wb") as f:
                Pickle.dump(mh_dict, f)

            rd.submit_to_cluster(pkl_file, n_jobs=2000)
            #
            # mh = MinimisationHandler(mh_dict)
            # mh.iterate_run(mh_dict["scale"], mh_dict["n_steps"], n_trials=100)
            # mh.clear()
            res[gamma] = mh_dict

        src_res[label] = res

    cat_res[cat] = src_res

rd.wait_for_cluster()

for (cat, src_res) in cat_res.iteritems():

    name = name_root + cat.replace(" ", "") + "/"

    sens = [[] for _ in src_res]
    fracs = [[] for _ in src_res]
    disc_pots = [[] for _ in src_res]
    sens_e = [[] for _ in src_res]
    disc_e = [[] for _ in src_res]

    labels = []

    for i, (f_type, res) in enumerate(sorted(src_res.iteritems())):

        for (gamma, rh_dict) in sorted(res.iteritems()):
            try:
                rh = ResultsHandler(rh_dict["name"], rh_dict["llh kwargs"],
                                    rh_dict["catalogue"])

                # raw_input("prompt")

                # The uptime can noticeably devaiate from 100%
                inj = rh_dict["inj kwargs"]["Injection Time PDF"]

                cat = np.load(rh_dict["catalogue"])

                inj_time = 0.

                for season in rh_dict["datasets"]:
                    time = TimePDF.create(inj, season)
                    inj_time += time.effective_injection_time(cat)

                astro_sens, astro_disc = rh.astro_values(
                    rh_dict["inj kwargs"]["Injection Energy PDF"])

                key = "Total Fluence (GeV^{-1} cm^{-2} s^{-1})"

                e_key = "Total Luminosity (erg/s)"

                sens[i].append(astro_sens[key] * inj_time)
                disc_pots[i].append(astro_disc[key] * inj_time)

                sens_e[i].append(astro_sens[e_key] * inj_time)
                disc_e[i].append(astro_disc[e_key] * inj_time)

                # raw_input("prompt")

                fracs[i].append(gamma)

            except OSError:
                pass

        labels.append(f_type)
        # plt.plot(fracs, disc_pots, linestyle="--", color=cols[i])

    for j, s in enumerate([sens, sens_e]):

        d = [disc_pots, disc_e][j]

        for k, y in enumerate([s, d]):

            plt.figure()
            ax1 = plt.subplot(111)

            cols = ["b", "orange", "green"]
            linestyle = ["-", "--"][k]

            for i, f in enumerate(fracs):
                plt.plot(f, y[i], label=labels[i], linestyle=linestyle,
                         color=cols[i])

            label = ["", "energy"][j]

            y_label = [r"Total Fluence [GeV cm$^{-2}$]",
                       r"Mean Isotropic-Equivalent $E_{\nu}$ (erg)"]

            ax1.grid(True, which='both')
            ax1.set_ylabel(y_label[j], fontsize=12)
            ax1.set_xlabel(r"Gamma")
            ax1.set_yscale("log")
            ax1.set_ylim(0.95 * min([min(x) for x in y]),
                         1.1 * max([max(x) for x in y]))

            print y

            plt.title("Time-Integrated Emission")

            ax1.legend(loc='upper right', fancybox=True, framealpha=1.)
            plt.tight_layout()

            print label, k

            plt.savefig(plot_output_dir(name) + "/spectral_index_" + label +
                        "_" + ["sens", "disc"][k] + ".pdf")
            plt.close()