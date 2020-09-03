# DMD_ScopeFoundry


Project for the implementation of Texas Instruments controller DLPC900 in ScopeFoundry. 
This project is based on another work (https://github.com/csi-dcsc/Pycrafter6500): the main difference is that here we use the hidapi python wrapper instead of the libusb library (that gives some errors while running). For further details about the protocol of communication, please refer to the guide (http://www.ti.com/lit/ug/dlpu018d/dlpu018d.pdf).



Some notes:



- Use dtype = numpy.bool for images.;
- It's important that the alphabetical order of the images of patterns is in the same order you want to load on the DMD. (The patterns names must contain a number as last characters, and be sure that these numbers contain the same number of digits, so 0005 and 1430 are good, while 005 and 1430 are not good);
- The code can manage only .png patterns, but the extension to other formats is really easy;
