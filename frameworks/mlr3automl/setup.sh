#!/usr/bin/env bash
HERE=$(dirname "$0")
VERSION=${1:-"stable"}
REPO=${2:-"https://github.com/a-hanf"}
MLR_REPO=${3:-"https://github.com/mlr-org"}

. $HERE/../shared/setup.sh "$HERE"
if [[ -x "$(command -v apt-get)" ]]; then
SUDO apt-get update
#SUDO apt-get install -y software-properties-common apt-transport-https libxml2-dev
#SUDO apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 51716619E084DAB9
#SUDO add-apt-repository 'deb [arch=amd64,i386] https://cran.rstudio.com/bin/linux/ubuntu bionic-cran35/'
SUDO apt-get install -y software-properties-common dirmngr
SUDO apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E298A3A825C0D65DFD57CBB651716619E084DAB9
SUDO add-apt-repository "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"
SUDO apt-get update
SUDO apt-get install -y r-base r-base-dev
SUDO apt-get install -y libgdal-dev libproj-dev
SUDO apt-get install -y libssl-dev libcurl4-openssl-dev
SUDO apt-get install -y libcairo2-dev libudunits2-dev
fi

# We install dependencies a subdirectory of the framework folder, because:
#   1. It allows different packages for different frameworks
#   2. The default package directory is not always writeable (e.g. on Github CI).
# This directory needs to be added to the path when executing the Rscript.
# We do this in `exec.py` by prepending a `.libPaths()` call.
mkdir "${HERE}/r-packages"

Rscript -e 'options(install.packages.check.source="no"); install.packages(c("mlr3", "mlr3pipelines", "mlr3misc", "mlr3oml", "mlr3hyperband", "mlr3tuning", "paradox"), repos="https://cloud.r-project.org/", lib="' "${HERE}/r-packages/" '")'
Rscript -e 'options(install.packages.check.source="no"); install.packages(c("remotes", "checkmate", "R6", "xgboost", "ranger", "LiblineaR", "emoa", "e1071", "glmnet"), repos="https://cloud.r-project.org/", lib="'"${HERE}/r-packages/"'")'
Rscript -e '.libPaths("'"${HERE}/r-packages/"'"); remotes::install_github("'"${MLR_REPO}"'/mlr3extralearners", lib="'"${HERE}/r-packages/"'")'
Rscript -e '.libPaths("'"${HERE}/r-packages/"'"); remotes::install_github("'"${REPO}"'/mlr3automl", lib="'"${HERE}/r-packages/"'")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3pipelines")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3oml")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/paradox")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3misc")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3tuning@autotuner-notimeout")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3@master")'
#Rscript -e 'remotes::install_github("'"${MLR_REPO}"'/mlr3hyperband@master")'

echo "HERE := ${HERE}"
Rscript -e '.libPaths("'"frameworks/mlr3automl/r-packages/"'"); packageVersion("mlr3automl")' | awk '{print $2}' | sed "s/[‘’]//g" >> "${HERE}/.installed"
