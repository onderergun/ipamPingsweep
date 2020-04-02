# ipamPingsweep
Runs a ping sweep through all the subnets in IPAM.

It sends the results in an email in any of the three below conditions: 

1- If an IP Address is allocated but DEAD.

2- If an IP Address is ALIVE but description says Reserved.

3- If an IP Address is not allocated but ALIVE.

Email parameters should be edited in the script.

Tested on CVP IPAM v1.1.0

