# Rhys Mac Giollabhuidhe, 21363479
import socket, pickle, os, time, sys, select, psutil
import numpy as np
import constants as const

buffer_size = 65535

def create_listening_socket(ip_address, port):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((ip_address, port))
    return s

def broadcast(exception, network_IPs, bytes_to_send):
    in_octs = exception[0].split('.')
    for IP in network_IPs:
        IP_octs = IP.split('.')
        if IP_octs[0:3] != in_octs[0:3]:
            soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            soc.bind((IP, 0))
            print(IP)
            soc.sendto(bytes_to_send, ("255.255.255.255", const.SERVER_PORT))
            soc.close()


def main(argv):
    time.sleep(30)

    interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
    all_IPs = [ip[-1][0] for ip in interfaces]
    network_IPs = []
    for ip in all_IPs:
        if not ip in network_IPs:
            network_IPs.append(ip)
    print(network_IPs)

    # structure: {target : next node in path to that target}
    routing_table = {}
    # structure: {target : time at which target was recorded}
    routing_timestamps = {}
    # structure: {message ID : previous node in path for that message}
    message_table = {}

    #sockets = {}
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("0.0.0.0", const.SERVER_PORT))
    #    sockets.update({IP : s})

    while True:
        #ready, _, _ = select.select(sockets, [], [])
        bytes_address_pair = s.recvfrom(buffer_size)

        altered_table = False
        timed_out = []
        for target in routing_timestamps.keys():
            now = time.time()
            now -= routing_timestamps[target]
            if now > const.FWD_INFO_TIMEOUT:
                altered_table = True
                timed_out.append(target)
                print("forwarding data for", target, "timed out")
        for target in timed_out:
            del routing_table[target]
            del routing_timestamps[target]
        if altered_table:
            print(routing_table)

        #for s in ready:
        if True:
            #bytes_address_pair = s.recvfrom(buffer_size)
            ID_message_pair = bytes_address_pair[0]
            address = bytes_address_pair[1]
            overhead = ID_message_pair[0]
            target   = int.from_bytes(ID_message_pair[1:3], byteorder='big')

            if not (address[0] in network_IPs): #if we didn't receive this message from ourselves
                if overhead & const.SEARCH == const.SEARCH: #if the incoming message is a search
                    if overhead & const.SCRUB_REQ == const.SCRUB_REQ: #if this is an outgoing scrub request
                        if target in routing_table.keys():
                            del routing_table[target]
                            if target in routing_timestamps.keys():
                                del routing_timestamps[target]

                        bytes_to_send = (overhead.to_bytes(1, byteorder='big')+
                                            target.to_bytes(2, byteorder='big'))
                        print("forwarding scrub request on:")
                        broadcast(address, network_IPs, bytes_to_send)

                        overhead = overhead-const.SEARCH
                        bytes_to_send = (overhead.to_bytes(1, byteorder='big')+
                                            target.to_bytes(2, byteorder='big'))
                        print("confirming scrub request for sender")
                        soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                        soc.sendto(bytes_to_send, (address[0], const.SERVER_PORT))
                        soc.close()


                    elif target == const.SEARCH_ALL: #if this is an outgoing search all
                        print("forwarding ID search on:")
                        broadcast(address, network_IPs, ID_message_pair)

                    else: #if this is an outgoing broadcast
                        if (not target in routing_table.keys()) or (routing_table[target] is None):
                        #if we haven't identified a path to the target yet
                            routing_table.update( {target : None} )
                            print("forwarding broadcast on:")
                            broadcast(address, network_IPs, ID_message_pair)

                        elif (target in routing_table.keys()) and ( not routing_table[target] is None):
                        #if we have already identified a path to the target
                            print("forwarding to", format(target, '04x'), "through", routing_table[target])
                            soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                            soc.sendto(ID_message_pair, (routing_table[target][0], const.SERVER_PORT))
                            soc.close()

                elif overhead & const.SCRUB_REQ == const.SCRUB_REQ: #if the incoming message is a return of a scrub req
                    print("forwarded scrub req successful")

                elif target == const.SEARCH_ALL: #if the incoming message is a return of a search all
                    print("ID search found")
                    soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                    soc.sendto(ID_message_pair, (message_table[(overhead & const.FOUND)], const.SERVER_PORT))
                    soc.close()

                else: #if the incoming message is a return of a regular broadcast
                    if (not target in routing_table.keys()) or (routing_table[target] is None):
                    #if we haven't identified a path to the target yet
                        print("search found")
                        routing_table.update({target : address})
                        stamp = time.time()
                        routing_timestamps.update({target : stamp})
                        print("When sending to", format(target, '04x'), "forward to", address)
                        soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                        soc.sendto(ID_message_pair, (message_table[(overhead & const.FOUND)], const.SERVER_PORT))
                        soc.close()

                    elif (target in routing_table.keys()) and ( not routing_table[target] is None):
                    #if we have already identified a path to the target
                        soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
                        soc.sendto(ID_message_pair, (message_table[(overhead & const.FOUND)], const.SERVER_PORT))
                        soc.close()


                if not (((overhead & const.FOUND) in message_table) or overhead & const.SCRUB_REQ == const.SCRUB_REQ):
                #if this is our first time to process this broadcast and it isn't a scrub request
                    message_table.update({(overhead & const.FOUND) : address[0]})

if __name__ == "__main__":
    main(sys.argv[1:])