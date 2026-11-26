# Secure Wireless Smart Car Door Unlocking System

Code and paper for a rolling-code scheme that locks and unlocks a car door over a wireless link. Every button press sends a one-time code derived from a shared seed and hashed, so a captured message cannot be replayed.

**Published:** Springer book chapter in *IoT Based Control Networks and Intelligent Systems* (ICICNIS 2022), Lecture Notes in Networks and Systems, vol. 528, pp. 99–112. DOI: [10.1007/978-981-19-5845-8_8](https://doi.org/10.1007/978-981-19-5845-8_8).

The repository holds the submitted paper (`ICICNIS_2022_paper_2358.pdf`), a second copy of the paper, the project report and the prototype code.

## Why it is interesting

- The car and the remote share a seed and a counter. Both draw the same sequence of random numbers from the seed, hash each one into a MAC, and hash that again with the action (`LOCK` or `UNLOCK`), so each code is used once and says what it is for.
- The car precomputes a window of the next 128 codes. A press that the car did not hear (the remote is ahead) still matches a later code in the window, and the car then moves its counter forward to resynchronise.

## Run it

The prototype in `Real Time Implementation using Pyfirmata/` runs on two machines on the same network: one as the car, one as the remote.

```bash
pip install pycryptodome numpy python-dotenv
python seed_generation.py   # writes seed.json; copy the same file to both machines
python car.py               # on the car machine: listens on port 5050
python remote.py            # on the remote machine: asks for LOCK or UNLOCK and sends the code
```

This is the code as it was in 2022, not maintained since:

- `car.py` uses `winsound`, so it runs on Windows. The Arduino calls through pyFirmata are present but commented out.
- `remote.py` has the car's IP address hard-coded; change `SERVER` to your car machine's address.
- `remote.py` hashes with MD5 while `car.py` compares against SHA-256, so the two must be made to use the same hash before they will match.
- `main.py` is a separate RSA (PKCS#1 OAEP) experiment; `rng.py`, `try.py` and `Modules/` are scratch files.

A reworked 2025 version, with the Arduino wired up through pyFirmata, is in [Secure-IoV-Unlocking-System](https://github.com/VarunAgarwalOfficial/Secure-IoV-Unlocking-System).

## Tech

Python, hashlib (SHA-256), sockets, pyFirmata and Arduino; PyCryptodome for the RSA experiment.

## Context

Research project at VIT Vellore, School of Computer Science and Engineering, 2022. The full author list is in the citation below.

## Cite

```bibtex
@incollection{Melarkode2022SmartCarDoor,
  title     = {Secure Wireless Smart Car Door Unlocking System},
  author    = {Melarkode, Navneet Vinod and Agarwal, Varun Niraj and Kanshi, Avaneesh and Lal, Anisha M.},
  booktitle = {IoT Based Control Networks and Intelligent Systems},
  series    = {Lecture Notes in Networks and Systems},
  volume    = {528},
  publisher = {Springer Nature Singapore},
  year      = {2022},
  pages     = {99--112},
  doi       = {10.1007/978-981-19-5845-8_8}
}
```

GitHub also reads `CITATION.cff` and shows a "Cite this repository" button.

## Status

Finished, as of 26 November 2026. The paper was published in LNNS volume 528 (2022). See [STATUS.md](STATUS.md).

## Licence

MIT, see LICENSE.
