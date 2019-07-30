"""
Your awesome Distance Vector router for CS 168
"""

import sim.api as api
import sim.basics as basics
import pdb

from dv_utils import PeerTable, PeerTableEntry, ForwardingTable, \
    ForwardingTableEntry

# We define infinity as a distance of 16.
INFINITY = 16

# A route should time out after at least 15 seconds.
ROUTE_TTL = 15


class DVRouter(basics.DVRouterBase):
    # NO_LOG = True  # Set to True on an instance to disable its logging.
    POISON_MODE = True  # Can override POISON_MODE here.
    # DEFAULT_TIMER_INTERVAL = 5  # Can override this yourself for testing.

    def __init__(self):
        """
        Called when the instance is initialized.

        DO NOT remove any existing code from this method.
        """
        self.start_timer()  # Starts calling handle_timer() at correct rate.

        # Maps a port to the latency of the link coming out of that port.
        self.link_latency = {}

        # Maps a port to the PeerTable for that port.
        # Contains an entry for each port whose link is up, and no entries
        # for any other ports.
        self.peer_tables = {}

        # Maps a port to the route most recently advertised
        self.routes_advertised = {}

        # A random index
        self.index = 0

        # Forwarding table for this router (constructed from peer tables).
        self.forwarding_table = ForwardingTable()

    def add_static_route(self, host, port):
        """
        Adds a static route to a host directly connected to this router.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.peer_tables, "Link is not up?"

        staticRoute = PeerTableEntry(host, 0, PeerTableEntry.FOREVER)
        self.peer_tables.get(port).update({host: staticRoute})
        self.update_forwarding_table()
        self.send_routes(force=False)

    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.link_latency[port] = latency
        self.peer_tables[port] = PeerTable()

        for host, ftEntry in self.forwarding_table.items():
            tempPacket = basics.RoutePacket(host, ftEntry.latency)
            self.send(tempPacket, port, flood=False)

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router does down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.peer_tables = {tempPort:tempTable for tempPort, tempTable in self.peer_tables.items() if tempPort != port}
        self.update_forwarding_table()
        self.send_routes(force=False)

    def handle_route_advertisement(self, dst, port, route_latency):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param dst: the destination of the advertised route.
        :param port: the port that the advertisement came from.
        :param route_latency: latency from the neighbor to the destination.
        :return: nothing.
        """
        neighborPeerTable = self.peer_tables.get(port)        
        ptEntry = PeerTableEntry(dst, route_latency, api.current_time() + ROUTE_TTL)
        neighborPeerTable.update({dst: ptEntry})
        self.peer_tables.update({port: neighborPeerTable})

        self.update_forwarding_table()
        self.send_routes(force=False)

    def update_forwarding_table(self):
        """
        Computes and stores a new forwarding table merged from all peer tables.

        :returns: nothing.
        """
        oldForwardingTable = dict(self.forwarding_table)

        self.forwarding_table.clear()  # First, clear the old forwarding table.

        for port, tempPeerTable in self.peer_tables.items():
            for host, entry in tempPeerTable.items():
                if ((self.forwarding_table.get(host, 110010100) == 110010100) 
                or ((entry.latency + self.link_latency.get(port)) < self.forwarding_table.get(host).latency)):
                    tempFTE = ForwardingTableEntry(host, port, self.link_latency.get(port) + entry.latency)
                    self.forwarding_table.update({host: tempFTE})

        # if (self.POISON_MODE):
        #     balogneList = []
        #     self.index = 50
        #     for oldKey, oldValue in oldForwardingTable.items():
        #         marker = True
        #         for key, value in self.forwarding_table.items():
        #             if (oldKey == key) and (oldValue == value):
        #                 marker = False
        #         if (marker):
        #             balogneList.append((oldKey, oldValue))
        
        #     loopTimer = api.current_time() + 15

        # while (self.index > 0):
        #     for port in self.peer_tables.keys():
        #         # Maybe not same port endless loop
        #         for tempRoute in balogneList:
        #             self.send(basics.RoutePacket(tempRoute[0], tempRoute[1].latency), port, flood=False)
        #     self.index = self.index - 1

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        forwardingTableEntry = self.forwarding_table.get(packet.dst, 110010100)
        if not (forwardingTableEntry == 110010100):
            if (in_port != forwardingTableEntry.port) and (forwardingTableEntry.latency < INFINITY):
                self.send(packet, forwardingTableEntry.port, flood=False)

    def send_routes(self, force=False):
        """
        Send route advertisements for all routes in the forwarding table.

        :param force: if True, advertises ALL routes in the forwarding table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
        :return: nothing.
        """
        listOfPorts = self.peer_tables.keys()
        ftEntries = self.forwarding_table.values()
        routes_advertised_toUpdate = []
        if (force):
            for ftEntry in ftEntries:
                for port in listOfPorts:
                    if (port != ftEntry.port):
                        tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)
                        self.send(tempPacket, port, flood=False) 
                        # self.routes_advertised.update({(ftEntry.dst, port): ftEntry.latency})
                        routes_advertised_toUpdate.append({(ftEntry.dst, port): ftEntry.latency})
                    elif ((self.POISON_MODE) and (port == ftEntry.port) and (ftEntry.latency != self.link_latency.get(port))):
                        tempPacket = basics.RoutePacket(ftEntry.dst, INFINITY)
                        self.send(tempPacket, port, flood=False)
                        # self.routes_advertised.update({(ftEntry.dst, port): ftEntry.latency})
                        routes_advertised_toUpdate.append({(ftEntry.dst, port): ftEntry.latency})
                self.routes_advertised.update({(ftEntry.dst, port): ftEntry.latency})

        else:
            # for host, entry in self.forwarding_table.items():
                # for port in listOfPorts:
        #             toSend = None
                    # if (port != entry.port):
                        # toSend = basics.RoutePacket(entry.dst, entry.latency if entry.latency < INFINITY else INFINITY)
                    # elif (self.POISON_MODE and port == entry.port and entry.latency != self.link_latency.get(port)):
        #                 toSend = basics.RoutePacket(entry.dst, entry.latency if entry.latency < INFINITY else INFINITY)
                    
        #             if (toSend != None):
        #                 if ((self.routes_advertised.get((entry.dst, port)) != (entry.latency)) or ((entry.dst, port) not in self.routes_advertised.keys())):
        #                     self.send(toSend, port, flood=False)
        #                     self.routes_advertised.update({(toSend.dst, port): toSend.latency})



# make packet -> compare packet latency history 


# key = (destination, port (advertised out of)) -> (latency)
                    # if (self.routes_advertised.get(port) == )
            # for ftEntry in ftEntries:
            #     for port in listOfPorts:
            #         if (self.POISON_MODE):
            #             if (port == ftEntry.port):
            #                 tempPacket = basics.RoutePacket(ftEntry.dst, INFINITY)
            #                 if ((not self.packet_in_list(tempPacket, self.routes_advertised.values())) 
            #                 or (not self.compare_packets(tempPacket, self.routes_advertised.get(ftEntry.port)))):
            #                     self.send(tempPacket, port, flood=False) 
            #                     self.routes_advertised.update({port: tempPacket})     
            #         if (port != ftEntry.port):
            #             tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)
            #             if ((not self.packet_in_list(tempPacket, self.routes_advertised.values())) 
            #             or (not self.compare_packets(tempPacket, self.routes_advertised.get(ftEntry.port)))):
            #                 self.send(tempPacket, port, flood=False) 
            #                 self.routes_advertised.update({port: tempPacket})


                    #     if ((not self.POISON_MODE) and (port != ftEntry.port)):
                    #         self.send(tempPacket, port, flood=False) 
                    #         self.routes_advertised.update({port: tempPacket})
                    # elif ((self.POISON_MODE) and (port == ftEntry.port) and (ftEntry.latency != self.link_latency.get(port))):
                    #     tempPacket = basics.RoutePacket(ftEntry.dst, INFINITY)
                    #     if ((not self.packet_in_list(tempPacket, self.routes_advertised.values())) 
                    #     or (not self.compare_packets(tempPacket, self.routes_advertised.get(ftEntry.port)))):
                    #         self.send(tempPacket, port, flood=False)    
                    #         self.routes_advertised.update({port: tempPacket})

            # for entry in ftEntries:
            #     for port in listOfPorts:
            #         if (port != entry.port):
            #             # self.send(tempPacket, port, flood=False) 
            #             # routes_advertised_toUpdate.append({(entry.dst, port): entry.latency})
            #             packetToSend = basics.RoutePacket(entry.dst, entry.latency if entry.latency < INFINITY else INFINITY) 

            #         elif (self.POISON_MODE):
            #             if ((port == entry.port) and (entry.latency != self.link_latency.get(port))):
            #                 packetToSend = basics.RoutePacket(entry.dst, INFINITY)

            #         else:
            #             packetToSend = basics.RoutePacket(entry.dst, -1)

            #         if ((self.routes_advertised.get((entry.dst, port)) != entry.latency) 
            #         or (self.history_checker(entry, port))):
            #             if (packetToSend.latency != -1): 
            #                 self.send(packetToSend, port, flood=False)
            #                 self.routes_advertised.update({(entry.dst, port): packetToSend.latency})
            #         else:
            #             continue

            #         routes_advertised_toUpdate.append({(entry.dst, port): entry.latency})
            # [self.routes_advertised.update(tempRoute) for tempRoute in routes_advertised_toUpdate]




            # 25/29 IMPLEMENTATION COPY
            for entry in ftEntries:
                tempPacket = basics.RoutePacket(entry.dst, entry.latency if entry.latency < INFINITY else INFINITY)
                for port in listOfPorts:
                    if ((self.routes_advertised.get((entry.dst, port)) != entry.latency) 
                    or (self.history_checker(entry, port))):
                        if (port != entry.port):
                            self.send(tempPacket, port, flood=False) 
                            # self.send_helper(tempPacket, port)
                            routes_advertised_toUpdate.append({(entry.dst, port): entry.latency}) 
                        if (self.POISON_MODE):

                            if ((port == entry.port) and (entry.latency != self.link_latency.get(port))):
                                tempPacket = basics.RoutePacket(entry.dst, INFINITY)
                                if ((self.routes_advertised.get((entry.dst, port)) != (entry.latency)) or ((entry.dst, port) not in self.routes_advertised.keys())):
                                    self.send(tempPacket, entry.port, flood=False)
                                    # self.send_helper(tempPacket, port)
                                    routes_advertised_toUpdate.append({(entry.dst, port): entry.latency})
                                tempPacket = basics.RoutePacket(entry.dst, entry.latency if entry.latency < INFINITY else INFINITY)

                    routes_advertised_toUpdate.append({(entry.dst, port): entry.latency})
            [self.routes_advertised.update(tempRoute) for tempRoute in routes_advertised_toUpdate]

            # # 23/29 IMPLEMENTATION
            # for ftEntry in ftEntries:
            #     tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)
            #     if ((not self.packet_in_list(tempPacket, self.routes_advertised.values())) 
            #     or (not self.compare_packets(tempPacket, self.routes_advertised.get(ftEntry.port)))):
            #         for port in listOfPorts:
            #             if (port != ftEntry.port):
            #                 self.send(tempPacket, port, flood=False) 
            #                 routes_advertised_toUpdate.append({ftEntry.port: tempPacket}) 
            #             if ((self.POISON_MODE) and (port == ftEntry.port) and (ftEntry.latency != self.link_latency.get(port))):
            #                 tempPacket = basics.RoutePacket(ftEntry.dst, INFINITY)
            #                 if ((not self.packet_in_list(tempPacket, self.routes_advertised.values())) 
            #                 or (not self.compare_packets(self.routes_advertised.get(ftEntry.port), tempPacket))):
            #                     self.send(tempPacket, ftEntry.port, flood=False)
            #                     routes_advertised_toUpdate.append({ftEntry.port: tempPacket})
            #                 tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)

            #         # routes_advertised_toUpdate.append({ftEntry.port: tempPacket})
            # [self.routes_advertised.update(tempRoute) for tempRoute in routes_advertised_toUpdate]
                



            # FIRST PART OF SEND
            # if (self.POISON_MODE):
            #     for ftEntry in ftEntries:
            #         for port in listOfPorts:
            #             if ((port == ftEntry.port) and (ftEntry.latency != self.link_latency.get(port))):
            #                 tempPacket = basics.RoutePacket(ftEntry.dst, INFINITY)
            #                 self.send(tempPacket, port, flood=False)
            #                 self.routes_advertised.update({port: tempPacket})
            #             else:
            #                 tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)
            #                 self.send(tempPacket, port, flood=False)
            #                 self.routes_advertised.update({port: tempPacket})

            # else:
            #     for ftEntry in ftEntries:
            #         tempPacket = basics.RoutePacket(ftEntry.dst, ftEntry.latency if ftEntry.latency < INFINITY else INFINITY)
            #         for port in listOfPorts:
            #             if (port != ftEntry.port):
            #                 self.send(tempPacket, port, flood=False)
            #                 self.routes_advertised.update({port: tempPacket})

    # def send_helper(self, packet, port):
    #     packetsAdvertisedList = self.routes_advertised.values()
    #     marker = True
    #     for tempRoute in packetsAdvertisedList:
    #         if ((tempRoute.latency == packet.latency) and (tempRoute.dst == packet.dst)):
    #             marker = False
    #     if (self.routes_advertised.get(port) == packet):
    #         marker = False

    #     if (marker):
    #         self.send(packet, port, flood=False)
    #         self.routes_advertised.update({port: packet})


    def compare_packets(self, packetA, packetB):
        """
        Compares the the destinations and latency of two packets to see if
        they equate to the same route. 
        """
        if (type(packetB) == type(None)):
            return False 
        if ((packetA.latency == packetB.latency) and (packetA.dst == packetB.dst)):
            return True
        return False

    def packet_in_list(self, packet, packetList):
        for tempPacket in packetList:
            if ((packet.latency == tempPacket.latency) and (packet.dst == tempPacket.dst)):
                return True
        return False

    def history_checker(self, entry, port):
        routeLatency = entry.latency
        destination = entry.dst

        for key, value in self.routes_advertised.items():
            # pdb.set_trace()
            if ((key[0] == destination) and (value ==routeLatency)):
                return False
        return True

    def expire_routes(self):
        """
        Clears out expired routes from peer tables; updates forwarding table
        accordingly.
        """
        for port, peerTable in self.peer_tables.items():
            peerTable = {host:ptEntry for host, ptEntry in peerTable.items() if ptEntry.expire_time > api.current_time()}
            self.peer_tables.update({port: peerTable})

        self.update_forwarding_table()

    def handle_timer(self):
        """
        Called periodically.

        This function simply calls helpers to clear out expired routes and to
        send the forwarding table to neighbors.
        """
        self.expire_routes()
        self.send_routes(force=True)

    # Feel free to add any helper methods!
