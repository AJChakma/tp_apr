# -*- coding: utf-8 -*-
"""
Created on Sun Nov 11 15:40:14 2018

@author: Alan-Jyoti
"""

import simpy, random
from scipy import mean
from math import sqrt
import numpy as np

def arrival(env, lambd):
    global nb_packets, buffer_length
    while True:
        nb_packets += 1
        buffer_length.append(nb_packets)
        #print("arrival", round(env.now,3), "nb_packets={}".format(nb_packets))
        yield env.timeout(random.expovariate(lambd))
        
def depart(env, mu):
    global nb_packets, buffer_length
    while True:
        if nb_packets > 0:
            nb_packets -= 1
        buffer_length.append(nb_packets)    
        print("depart", round(env.now,3), "nb_packets={}".format(nb_packets))
        yield env.timeout(random.expovariate(mu))
 
random.seed(42)
observed_packet_rate = []
nb_simulation = 100
for i in range(0,nb_simulation):
    nb_packets = 0
    buffer_length = []
    env = simpy.Environment()
    env.process(arrival(env,15))
    #env.process(depart(env,20))
    simulation_duration = 100
    env.run(until=simulation_duration)
    observed_packet_rate.append(nb_packets/simulation_duration)
    
mean_packet_rate = mean(observed_packet_rate)
bound = 1.96*np.std(observed_packet_rate)/sqrt(nb_simulation)
print("Mean observed packet rate: {}".format(mean_packet_rate))
print("Confidence interval (95%): [{}, {}]".format(mean_packet_rate - bound, mean_packet_rate + bound))   