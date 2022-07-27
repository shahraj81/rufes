FROM python:3.9.5
MAINTAINER shahzad.rajput@nist.gov

# Set timezone
RUN ln -fs /usr/share/zoneinfo/America/New_York /etc/localtime

# Install system packages
RUN apt-get update && apt-get install -y \
    git \
    make \
    tzdata \
    vim

# Reconfigure tzdata
RUN dpkg-reconfigure -f noninteractive tzdata

#-------------------------------------------------------------
# Upgrade pip and install munkres
#-------------------------------------------------------------

RUN python3.9 -m pip install --upgrade pip 
RUN pip3.9 install munkres

#-------------------------------------------------------------
# Install neleval and scipy
#-------------------------------------------------------------

RUN pip install neleval
RUN pip install scipy

# Setup the AIDA repository
WORKDIR /scripts

RUN git clone https://github.com/shahraj81/rufes.git

# Setup the scripts directory
COPY ./scripts/* ./
RUN cp /scripts/rufes/tools/scorer/score_submission.py /scripts/
RUN cp /scripts/rufes/input/log_specifications.txt /scripts/

WORKDIR /scripts/

#-------------------------------------------------------------
#  Setup entrypoint
#-------------------------------------------------------------

ENTRYPOINT ["make"]
