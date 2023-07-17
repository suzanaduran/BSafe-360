# BSafe-360: A naturalistic cycling data collection tool

This repository was created as part of Suzana Duran Bernardes' Ph.D. dissertation. It contains the information needed for reproducing the BSafe-360 device, which is a portable and customizable multi-sensor device. The idea behind the development of the BSafe-360 device was to have an all-in-one tool that facilitated cycling data collection without needing to spend thousands of dollars and brought state-of-the-art practices to bicycle safety studies.

### Hardware
The [hardware](hardware) folder contains a list of the components used in the device.
<!-- all the instructions required for assembling one unit of the BSafe-360. It includes the circuit information, soldering tips, schematics, and enclosure 3D design and mold. -->

## Software
The codes needed for collecting and storing the data are written in Python 3. You can find them in the [python_scripts](python_scripts) folder.

- [connbike_10.py](python_scripts/connbike_10.py): This is the script responsible for reading the data from the sensors, making any required transformation to the data, and locally storing the data in the SQLite database.
- [load_postgre_v5.py](python_scripts/load_postgre_v5.py): This is the script responsible for reading the data in the local SQLite database and sending it to a PostgreSQL database in a server.

### Running scripts at startup
To make sure the device is collecting data as soon as the RPi is on, you can run the following command in your RPi terminal:
```
sudo nano /etc/rc.local
```
then, add the following lines right before the exit line:
```
sudo python3 /home/pi/connbike_10.py &
sudo python3 /home/pi/load_postgre_v5.py &
```
make sure to include the & sign in the end of each line to guarantee access to the OS system while the programs run in the background.

## Citation
You can cite this work through our paper:

MDPI and ACS Style
Duran Bernardes, S.; Ozbay, K. BSafe-360: An All-in-One Naturalistic Cycling Data Collection Tool. Sensors 2023, 23, 6471. https://doi.org/10.3390/s23146471

AMA Style
Duran Bernardes S, Ozbay K. BSafe-360: An All-in-One Naturalistic Cycling Data Collection Tool. Sensors. 2023; 23(14):6471. https://doi.org/10.3390/s23146471

Chicago/Turabian Style
Duran Bernardes, Suzana, and Kaan Ozbay. 2023. "BSafe-360: An All-in-One Naturalistic Cycling Data Collection Tool" Sensors 23, no. 14: 6471. https://doi.org/10.3390/s23146471


