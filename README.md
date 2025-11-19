# lamp\_stack #

Full stack for LAMP containerization, setup and deployment - **heavily
influenced by [lemurs_stack](https://gitlab.com/murs/lemurs/lemurs_stack) and
[csp_stack](https://gitlab.com/lbl-anp/csp/csp_stack/)**.

To get started:

* Read our [Submodule Primer](doc/submodule_primer.md) to become acquainted with
  using git submodules
* Use the `--recursive` flag when cloning this repo to ensure the submoduled
  repositories are included
  * `git clone --recursive https://gitlab.com/lbl-anp/lamp_stack`
* Make sure you have the git credential cache enabled so you don't have to
  authenticate for every submodule
* The first time you clone, make sure to `pre-commit install` somewhere in
  the repo (`pip3 install pre-commit` if you don't have it)

Deployments were previously managed by `kubernetes`, but this has been replaced
with `docker compose` (v2). See
[the lamp\_stack compose documentation](doc/lamp_compose.md) for information.

[[_TOC_]]

## Documentation Links ##

* Everything you need to know about submodules is in our
  [submodule primer](doc/submodule_primer.md)
* Read up on how we manage system configurations and how to add a new
  system config [here](doc/config_howto.md)
* Instructions on how to set up a fresh LAMP system is [here](doc/setup.md)
* Docker image building and related continuous integration info is
  [here](docker/images/README.md), as well as important info on running
  recons with these images
* Info on running characterization scans with the RIG is
  [here](doc/rig_characterization.md)
* Details of the `lamp_stack` compose deployment are
  [here](doc/lamp_compose.md)
* Using [Chrome Remote Desktop](doc/remote_access.md) for remote management
  of a LAMP system

## LAMP Systems ##

Each system has specific settings for various sensors, depending on what is
behind deployed. See the below documents for information.

### Available Systems ###

* [nglamp](doc/systems/nglamp.md)
* [prism\_v1](doc/systems/prism_v1.md)
* [prism\_v2](doc/systems/prism_v2.md)
* [polaris\_v2](doc/systems/polaris_v2.md)
* [labr](doc/systems/labr.md)
* [slamp](doc/systems/slamp.md)
* [clamp](doc/systems/clamp.md)
* [gegi\_v2](doc/systems/gegi_v2.md)
* [radarlamp](doc/systems/radarlamp.md)

## Non-LAMP Systems ##

There are two operating modes to consider - bare metal and dockerized. In
general, running bare metal on a NUC should work the best, since this is the
hardware we deploy on. However, deployments are fully dockerized in practice.

First, make sure docker is installed: <https://docs.docker.com/get-docker/>.

On MacOS, **make sure to increase the amount of memory containers have
access to.** See [these instructions](https://docs.docker.com/desktop/mac/). You
will also have to manually enable the setting to have it start automatically on
boot.

If using the `radkit` or `radkit_lamp` images, especially if doing
reconstructions, make sure to **read the
[`radkit` image documentation](docker/images/radkit/README.md) first**.
Reconstructions will typically require using the GPU, which is not available
in containers on MacOS. You must run recons bare metal on MacOS to use the GPU.
On NUCs, the Intel GPU (`/dev/dri`) can be mounted into the container and used
with `--privileged`.

If doing extended development bare metal on a NUC, it's recommended to use
[conda environments](https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html)
to keep things isolated/organized.

If developing on MacOS, conda environments are always recommended.

## Development ##

This repository uses [pre-commit](https://pre-commit.com/). `pip install
pre-commit`, then run `pre-commit install` anywhere in the repository. Any
files you commit will be checked against the pre-commit hooks listed in
`.pre-commit-config.yaml`, which will fix or make consistent common formatting
issues.
