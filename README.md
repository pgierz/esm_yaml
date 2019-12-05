# esm-tools

Small tools with big impact for Earth System Modelling

This repository is the entry point to get all esm-tools. It provides an installer to get all esm-tools which include
* esm-master
* esm-environment
* esm-runscripts
* esm-usermanual

## Downloading and installing esm-tools
### Downloading esm-tools installer
To download the esm-tools installer just clone the esm-tools repository from GitLab:
```
git clone https://<yourdkrzusername>@gitlab.dkrz.de/esm-tools/esm-tools.git
```
### esm-tools installation
After downloading the esm-tools repository you can install all esm-tools by simply running:
```sh
cd esm-tools
./install.sh
```

<!---### Using pip
```sh
pip install esm-tools
```

## Install `conda`

[What is `conda`?](https://docs.conda.io/projects/conda/en/latest/)

```sh
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# let the installer set your PATH variable
```

## Upload new version to PyPI

[What is PyPI?](https://pypi.org/)

```sh
python setup.py sdist
twine upload dist/esm-tools-2019.0.0.tar.gz
```
-->

## Documentation

[esm-usermanual (pdf)](https://gitlab.dkrz.de/esm-tools/esm-usermanual/blob/release/esm_usermanual.pdf)

[esm-usermanual (repository)](https://gitlab.dkrz.de/esm-tools/esm-usermanual)

### Wiki
[Wiki pages](https://gitlab.dkrz.de/esm-tools/esm-tools/wikis/home)

## Contributing

### What is the name of the stable/master/release branch?
The current "user-friendly" branch is `release`. Development work branches off from `develop`. We loosely try to follow the guidelines [here](https://nvie.com/posts/a-successful-git-branching-model/) to varying degrees of rigour.

### How does a pull request work?
1. Open an issue and describe your problem. Please include your currently used versions of:
   + `esm-master`, `esm-runscripts`, `esm-environment` (see the still unfinished !26, which will make this easier) 
   + machine
   + model (if possible, also here with version number)
2. If you have a fix for the problem, make a branch that starts from `develop` and post a merge request, labelling it as WIP.
3.  Ensure that your new code can produce a "sensible" simulation.
4. Describe the changes in your merge request, and document any new switches/variables/ect
5. One of the maintainers (@a270058 or @a270089) will merge it.

### Who is responsible?
The current permissions declare that only repository owners can merge. For now, that's Dirk and Nadine. Personally, I find it easier to have many small branches on my own, and one main one which eventually will get merged to develop. That way I can still follow bugs in my own code and see what caused them, without getting confused by changes from other developers.

See also #25 for more information regarding contributions.

