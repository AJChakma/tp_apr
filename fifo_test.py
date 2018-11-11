# -*- coding: utf-8 -*-
"""
Created on Mon Oct 22 08:34:13 2018

@author: Alan-Jyoti
"""
import random, math
import matplotlib.pyplot as plt

class Simulation:
    # Initialization of simulation
    def __init__(self, lambd, mu):
        self.lambd = lambd
        self.mu = mu
        self.num_in_system = 0
        self.clock = 0.0
        self.t_arrival = self.clock + self.neg_exp(self.lambd)
        self.t_depart = float('inf')
        
    # Handle arrival event
    def handle_arrival(self):
        self.num_in_system += 1
        if self.num_in_system == 1:
            self.t_depart = self.clock + self.neg_exp(self.mu)
        self.t_arrival = self.clock + self.neg_exp(self.lambd)
    
    # Handle depart event
    def handle_depart(self):
        self.num_in_system -= 1
        if self.num_in_system > 0:
            self.t_depart = self.clock + self.neg_exp(self.mu)
        else:
            self.t_depart = float('inf')
    
    def advance_time(self):
        t_event = min(self.t_arrival, self.t_depart)
        
        self.clock = t_event
        
        if t_event == self.t_arrival:
            self.handle_arrival()
        else:
            self.handle_depart()
        
    def neg_exp(self, param):
        return -1/param*math.log(random.random())
    
    

def fifo_simulation(lambd=1, mu=1, sim_time=100):
    sim = Simulation(lambd,mu)
    x = [0]
    while sim.clock < sim_time:
        print("Number of customers in queue: {}".format(sim.num_in_system))
        x.append(sim.num_in_system)
        sim.advance_time()
    fig, ax = plt.subplots()
    ax.plot(x)
    
    ax.set(xlabel='time (s)', ylabel='Number of customers in system',
           title='Queue simulation, lambda={}, mu={}'.format(lambd,mu),
           ylim=(0,50))
    ax.grid()
    
    plt.show()
            
    

