#!/usr/bin/env python3.7
"""
    Ensimag 2018 TP Perf.
"""

import simpy
import math
import numpy as np
from random import expovariate, uniform
import matplotlib.pyplot as plt

class Packet(object):
    """ Packet structure

    Attributes:
        id (int):
            Packet identifier
        size (int):
            Packet size in Bytes.
        generation_timestamp (float):
            Timestamp (simulated time) of packet generation
        output_timestamp (float):
            Timestamp (simulated time) when packet leaves a system
    """
    def __init__(self, id, size, generation_timestamp, source):
        self.id=id
        self.size=size
        self.generation_timestamp=generation_timestamp
        self.output_timestamp=0

class Source(object):
    """ Packet generator

    Attributes:
        env (simpy.Environment):
            Simulation environment
        name (str):
            Name of the source
        gen_distribution (callable):
            Function that returns the successive inter-arrival times of the packets
        size_distribution (callable):
            Function that returns the successive sizes of the packets
        init_delay (int):
            Starts generation after an initial delay. Default = 0
        destination (object):
            Entity that receives the packets from the generator
        debug (bool):
            Set to true to activate verbose debug
    """
    def __init__(self, env, name, init_delay=0, gen_distribution=lambda:1, size_distribution=lambda:1000,debug=False):
        self.env=env
        self.name=name
        self.init_delay=init_delay
        self.gen_distribution=gen_distribution
        self.size_distribution=size_distribution
        self.packet_count=0
        self.debug=debug
        self.destination= None
        self.action= env.process(self.run())

    def run(self):
        """ Packet generation loop

        """
        # Initial waiting time
        yield self.env.timeout(self.init_delay)
        while True:
            yield self.env.timeout(self.gen_distribution())
            packet_size=self.size_distribution()
            generated_packet= Packet(id=self.packet_count,size=packet_size,generation_timestamp=env.now, source=self.name)
            if self.debug:
                print("Packet (id=%d,size=%d) generated by %s at %f" %(self.packet_count, packet_size, self.name,
                    generated_packet.generation_timestamp))
            if self.destination is not None:
                if self.debug:
                    print("%s => %s" % (self.name, self.destination.name))
                self.destination.put(generated_packet)
            self.packet_count+=1

    def attach(self, destination):
        """ Method to set a destination for the generated packets

        Args:
            destination (QueuedServer || XMonitor):
        """
        self.destination= destination



class QueuedServer(object):
    """ Represents a waiting queue and an associated server.
    Attributes:
        env (simpy.Environment):
            Simulation environment
        name (str):
            Name of the source
        buffer (simpy.Store):
            Simpy FIFO queue
        buffer_max_size (int):
            Maximum buffer size in bytes
        buffer_size (int):
            Current size of the buffer in bytes
        service_rate (float):
            Server service rate in byte/sec
        destination (object):
            Entity that receives the packets from the server
        debug (bool):
            Set to true to activate verbose debug
        busy (bool):
            Is set if packet is currently processed by the server
        packet_count (int):
            Number of packet received
        packet_drop (int):
            Number of packets dropped


    """

    def __init__(self, env, name, channel, buffer_max_size=None, service_rate=1000,
                 debug=False, packet_list=[], random_delay=lambda:uniform(0,1)):
        self.env= env
        self.name= name
        self.channel= channel
        self.buffer= simpy.Store(self.env,capacity=math.inf) # buffer size is limited by put method
        self.buffer_max_size= buffer_max_size
        self.buffer_size=0
        self.service_rate= service_rate
        self.destination=None
        self.debug=debug
        self.busy=False
        self.collision=False
        self.packet_count=0
        self.packets_drop=0
        self.action= env.process(self.run())
        self.packet_list = []
        self.random_delay = random_delay

    def run(self):
        """ Packet waiting & service loop

        """
        waiting_packet = None
        while True:
            if waiting_packet is not None:
                packet = waiting_packet
                waiting_packet = None
            else:
                packet = yield self.buffer.get()
            self.channel.add_sender(self)
            yield self.env.timeout(packet.size/self.service_rate)
            self.channel.remove_sender(self)
            packet.output_timestamp= env.now


            if self.destination is None:
                self.packet_list.append(packet)
            if (not self.collision):
                if self.destination is not None:
                    self.destination.put(packet)
                self.channel.packet_list.append(packet)
            else:
                if self.debug:
                    print("Packet %d is discarded. Reason: Collision"
                          % (packet.id))
                self.packets_drop += 1
                waiting_packet = packet
                self.collision = False
                yield self.env.timeout(self.random_delay())

    def put(self, packet):
        self.packet_count += 1
        buffer_futur_size = self.buffer_size + packet.size

        if (self.buffer_max_size is None or buffer_futur_size <= self.buffer_max_size):
            self.buffer_size = buffer_futur_size
            self.buffer.put(packet)
            if self.debug:
                print("Packet %d added to queue %s." % (packet.id, self.name))
        else:
            if self.debug:
                print("Packet %d is discarded by queue %s. Reason: Buffer overflow." % (packet.id, self.name))

    def attach(self, destination):
        """ Method to set a destination for the serviced packets
        Args:
            destination (QueuedServer || XMonitor):
        """
        self.destination=destination

class Channel(object):
    def __init__(self, env, name, service_rate, collision, debug=False):
        self.env = env
        self.name = name
        self.senders_list = []
        self.service_rate = service_rate
        self.collision = collision
        self.busy = False
        self.debug = debug
        self.packet_list = []

    def add_sender(self, sender):
        self.senders_list.append(sender)
        self.busy = True
        if len(self.senders_list) > 1 and self.collision:
            self.broadcast_collision()

    def remove_sender(self, sender):
        self.senders_list.remove(sender)
        if len(self.senders_list) == 0:
            self.busy = False

    def broadcast_collision(self):
        if self.debug:
            print("Broadcast_collision")
        for sender in self.senders_list:
            sender.collision = True




class QueuedServerMonitor(object):
    """ A monitor for a QueuedServer. Observes the packets in service and in
        the queue and records that info in the sizes[] list. The monitor looks at the queued server
        at time intervals given by the sampling dist.

        Attributes:
        env (simpy.Environment):
            Simulation environment
        queued_server (QueuedServer):
            QueuedServer to monitor
        sample_distribution (callable):
            Function that returns the successive inter-sampling times
        sizes (list[int]):
            List of the successive number of elements in queue. Elements can be packet or bytes
            depending on the attribute count_bytes
        count_bytes (bool):
            If set counts number of bytes instead of number of packets
    """
    def __init__(self, env, queued_server, sample_distribution=lambda:1, count_bytes=False):
        self.env= env
        self.queued_server= queued_server
        self.sample_distribution= sample_distribution
        self.count_bytes= count_bytes
        self.sizes= []
        self.time_count=0
        self.action= env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.sample_distribution())
            self.time_count+=1
            if self.count_bytes:
                total= self.queued_server.buffer_size
            else:
                total= len(self.queued_server.buffer.items) + self.queued_server.busy
            self.sizes.append(total)

if __name__=="__main__":
    # Link capacity 64kbps
    process_rate= 64000/8 # => 8 kBytes per second
    # Packet length exponentially distributed with average 400 bytes
    dist_size= lambda:expovariate(1/400)
    # Packet inter-arrival time exponentially distributed
    gen_dist= lambda:expovariate(7.5) # 15 packets per second


    max_d = 100
    d_list = np.arange(0,max_d,10)
    nb_messages = []
    sub_nbmessages = []
    d_delays = []
    latency = []
    packet_drop_av = []
    for d in d_list:
        random_delay_aloha = lambda:uniform(0,d)
        packet_drop_ratio1 = []
        packet_drop_ratio2 = []
        packet_drop_ratio_tot = []
        latency_intermediate = []

        simulation_time = 100
        nb_simulations = 10
        for i in range(nb_simulations):
            env= simpy.Environment()
            src1= Source(env, "Source 1",gen_distribution=gen_dist,size_distribution=dist_size,debug=False)
            src2= Source(env, "Source 2",gen_distribution=gen_dist,size_distribution=dist_size,debug=False)
            ch= Channel(env,"Channel", service_rate=process_rate, collision=True, debug=False)
            qs1= QueuedServer(env,"Router1", channel=ch, random_delay=random_delay_aloha,
                              buffer_max_size=math.inf, service_rate=process_rate,debug=False)
            qs2= QueuedServer(env,"Router2", channel=ch, random_delay=random_delay_aloha,
                              buffer_max_size=math.inf, service_rate=process_rate,debug=False)
            # Link Source 1 to Router 1
            src1.attach(qs1)
            src2.attach(qs2)
            # Associate a monitor to Router 1
            qs1_monitor=QueuedServerMonitor(env,qs1,sample_distribution=lambda:1,count_bytes=False)
            qs2_monitor=QueuedServerMonitor(env,qs2,sample_distribution=lambda:1,count_bytes=False)
            env.run(until=simulation_time)
            #print("Packets: %d, Dropped packets: %d" % (src1.packet_count + src2.packet_count,
            #                                            qs1.packets_drop + qs2.packets_drop))

            #Latency
            simulation_latency = []
            for i,v in enumerate(ch.packet_list):
                simulation_latency.append(v.output_timestamp - v.generation_timestamp)
            if (len(simulation_latency) > 0):
                latency_intermediate.append(np.mean(simulation_latency))

            #Packet drop ratio
            packet_drop_ratio1.append(qs1.packets_drop/ (qs1.packet_count + qs1.packets_drop))
            packet_drop_ratio2.append(qs2.packets_drop/ (qs2.packet_count + qs2.packets_drop))
            packet_drop_ratio_tot.append((qs1.packets_drop + qs2.packets_drop) / (qs1.packet_count + qs1.packets_drop + qs2.packet_count + qs2.packets_drop))

            sub_nbmessages.append(qs1_monitor.sizes[-1] + qs2_monitor.sizes[-1])
        latency.append(np.mean(latency_intermediate))
        nb_messages.append(np.mean(sub_nbmessages))
        packet_drop_av.append(np.mean(packet_drop_ratio_tot))

    fig, (ax1, ax2, ax3) = plt.subplots(1,3)
    fig.set_figwidth(15,True)    
    fig.set_figheight(4,True)
    fig.suptitle("Pure Aloha")
    ax1.set_xlabel("d")
    ax1.set_ylabel("Latency")
    ax1.set_ylim(0,50)
    ax1.set_title("Influence of delay on latency")
    ax1.plot(d_list,latency)

    ax2.set_xlabel("d")
    ax2.set_ylabel("Number of pending messages")
    ax2.set_ylim(500,1500)
    ax2.set_title("Influence of delay on number of pending messages")
    ax2.plot(d_list,nb_messages)

    ax3.set_xlabel("d")
    ax3.set_ylabel("Total drop ratio")
    ax3.set_ylim(0,1)
    ax3.set_title("Influence of delay on drop ratio")
    ax3.plot(d_list,packet_drop_av)
    fig.show()
    

    round_power = 3
    #Latency
    mean_latency = np.mean(latency)
    bound = 3*np.std(latency)/np.sqrt(nb_simulations)
    print("Mean latency: {}".format(round(mean_latency,round_power)))
    print("Confidence interval (99%): [{}, {}]".format(round(mean_latency - bound,round_power), round(mean_latency + bound,round_power)))

    #Packet drop ratio
    mean_packet_drop_ratio1 = np.mean(packet_drop_ratio1)
    bound = 3*np.std(packet_drop_ratio2)/np.sqrt(nb_simulations)
    print("Packet drop ratio for Router1: {}".format(round(mean_packet_drop_ratio1,round_power)))
    print("Confidence interval (99%): [{}, {}]".format(round(mean_packet_drop_ratio1 - bound,round_power), round(mean_packet_drop_ratio1 + bound,round_power)))

    mean_packet_drop_ratio2 = np.mean(packet_drop_ratio2)
    bound = 3*np.std(packet_drop_ratio2)/np.sqrt(nb_simulations)
    print("Packet drop ratio for Router2: {}".format(round(mean_packet_drop_ratio2,round_power)))
    print("Confidence interval (99%): [{}, {}]".format(round(mean_packet_drop_ratio2 - bound,round_power), round(mean_packet_drop_ratio2 + bound,round_power)))