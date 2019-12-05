#!/usr/bin/env bash
module load git
echo "==================================================================================================="     
echo " Installing esm-tools."
echo " Author: Nadine Wieters (nadine.wieters@awi.de)" 
echo "==================================================================================================="     
echo " Usage: "
echo "          make install   "
echo " Output: "
echo "          Will clone the following esm-tools repositories: "
echo "          - esm-master"
echo "          - esm-environment"
echo "          - esm-runscripts"
echo "          - esm-usermanual"
echo ""
echo "===================================================================================================" 

get_repo () 
{
    git clone https://${DKRZ_GITLAB_USERNAME}@gitlab.dkrz.de/esm-tools/$1.git
}

install_subtools() 
{
	for esmtoolb in esm-environment esm-runscripts esm-usermanual; do
        # Check if esm-tool is not already installed
        if ! [ -d ${esmtoolb} ]; then
            echo "Installing ${esmtoolb}"
            # Check if variable for gitlab username is set or passed as argument
            if [[ $1 = "" && ${DKRZ_GITLAB_USERNAME} = "" ]]; then
                read -p 'Type in your DKRZ GitLab username: ' DKRZ_GITLAB_USERNAME
                echo ${DKRZ_GITLAB_USERNAME}
            # Check if gitlab username is passed as argument
            elif [[ $1 != "" ]]; then
                DKRZ_GITLAB_USERNAME=$1
            fi
            # Clone the repository that is not already installed
            get_repo ${esmtoolb}
        else
            echo "esm-tool ${esmtoolb} already installed."
        fi
	done
    # Calling ./set_links.sh always, even if everything is already installed
    cd esm-runscripts/functions/
    ./set_links.sh
}

# Save gitlab password for 300 sec
git config --global credential.helper 'cache --timeout=300'
DKRZ_GITLAB_USERNAME=''

for esmtoola in esm-master; do
    # Check if esm-master is not alleady installed
    if ! [ -d ${esmtoola} ]; then
        # Check if gitlab username is set
        if [[ ${DKRZ_GITLAB_USERNAME} = "" ]]; then
            read -p 'Type in your DKRZ GitLab username: ' DKRZ_GITLAB_USERNAME
            echo ${DKRZ_GITLAB_USERNAME}
        fi
        # Clone esm-master repository if not already installed
        get_repo ${esmtoola}
		cd esm-master
        # Install other esm-tools (esm-runscripts, esm-usermanual, esm-environment)
        install_subtools ${DKRZ_GITLAB_USERNAME}
    else
        # Install other esm-tools if needed (esm-runscripts, esm-usermanual, esm-environment)
        echo "esm-tool ${esmtoola} already installed."
		cd esm-master
        install_subtools ${DKRZ_GITLAB_USERNAME}
    fi
done


