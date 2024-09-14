# Rhys Mac Giollabhuidhe, 21363479
import socket, pickle, os, time, sys, random, psutil
import numpy as np
import constants as const
from time import sleep

local_IP = "0.0.0.0"
buffer_size = 65535

def get_broadcasting_addresses(IP_addresses):
    ret = []
    for address in IP_addresses:
        octets = address.split('.')
        octets[-1] = '255'
        updated_IP = '.'.join(octets)
        ret.append(updated_IP)

    return ret

def main(argv):
    time.sleep(90)
    tick = 1

    interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
    all_IPs = [ip[-1][0] for ip in interfaces]
    print(all_IPs)
    network_IPs = []
    for IP in all_IPs:
        if not IP in network_IPs:
            network_IPs.append(IP)
    print(network_IPs)
    broadcasting_addresses = get_broadcasting_addresses(network_IPs)
    print(broadcasting_addresses)

    local_ID = int(argv[0], 16)
    print("ID:", format(local_ID, '04x'))
    state = argv[1]
    print(state)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("0.0.0.0", const.SERVER_PORT))

    past_broadcasts = []

    sleep(5)
    scrubbing = False

    while True:
        ID_req_broadcast = const.SEARCH + random.randint(0, 63)
        if not ID_req_broadcast in past_broadcasts:
            past_broadcasts.append(ID_req_broadcast)
            break
    target = const.SEARCH_ALL
    bytes_to_send = (ID_req_broadcast.to_bytes(1, byteorder='big') +
                     target.to_bytes(2, byteorder='big') +
                     local_ID.to_bytes(2, byteorder='big'))
    for i in range(len(broadcasting_addresses)):
        soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print("broadcast", format(ID_req_broadcast, '07b'), "requesting IDs from other endpoints")
        soc.bind((broadcasting_addresses[i], 0))
        soc.sendto(bytes_to_send, (broadcasting_addresses[i], const.SERVER_PORT))
        soc.close()

    other_endpoint_IDs = []
    while True:
        # Listen for incoming datagrams
        while state == "listen":

            bytes_address_pair = s.recvfrom(buffer_size)
            print(":O! for me?")
            ID_message_pair = bytes_address_pair[0]
            address         = bytes_address_pair[1]
            overhead        = ID_message_pair[0]
            target          = int.from_bytes(ID_message_pair[1:3], byteorder='big')

            if (not address[0] in network_IPs): #if we didn't receive this message from ourselves

                if overhead + const.SEARCH in past_broadcasts:
                    if overhead + const.SEARCH == ID_req_broadcast: #if this message is a return of our ID request
                        content = int.from_bytes(ID_message_pair[3:5], byteorder='big')
                        print("acknowledging endpoint", format(content, '04x'))
                        other_endpoint_IDs.append(content)
                        state = "send"


                    else:
                        if overhead & const.SCRUB_REQ == const.SCRUB_REQ: #if this message is a return of our scrub request
                            print("routing data was scrubbed. DCing...")
                            s.close()
                            state = ""
                            break
                        else:   #if this message is a return of a past broadcast
                            print("receipt of broadcast", format(overhead, '07b'), "confirmed")
                            state = "send"

                elif target == local_ID: #if this is a broadcast for us
                    print(":D! for me!")
                    overhead &= const.FOUND
                    bytes_to_send = (overhead.to_bytes(1, byteorder='big') +
                                     target.to_bytes(2, byteorder='big'))
                    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    soc.bind((broadcasting_addresses[0],0))
                    time.sleep(1)
                    print("returning confirmation of message receipt")
                    soc.sendto(bytes_to_send, ("255.255.255.255", const.SERVER_PORT))
                    soc.close()

                    #origin = int.from_bytes(ID_message_pair[3:5], byteorder='big')
                    content = ID_message_pair[3:]
                    content = content.decode('utf-8')
                    #print("message received from", format(origin, '04x'), ":", content)
                    print("message:", content)

                elif target == const.SEARCH_ALL: #if this is a search all by another node
                    origin = int.from_bytes(ID_message_pair[3:5], byteorder='big')
                    print("endpoint", format(origin, '04x'), "requesting ID")
                    overhead &= const.FOUND
                    content = local_ID
                    bytes_to_send = (overhead.to_bytes(1, byteorder='big') +
                                     target.to_bytes(2, byteorder='big') +
                                     content.to_bytes(2, byteorder='big'))
                    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    soc.bind((broadcasting_addresses[0],0))
                    time.sleep(1)
                    print("returning ID to sender")
                    soc.sendto(bytes_to_send, ("255.255.255.255", const.SERVER_PORT))
                    soc.close()

                elif overhead & const.SCRUB_REQ == const.SCRUB_REQ: #if this is another node's scrub request
                    if target in other_endpoint_IDs:
                        print("scrub request received, erasing data...")
                        other_endpoint_IDs.remove(target)

                else:
                    print("not for me U_U")

            else:
                print("Not for me, /from/ me o_O")

        # make things happen
        while state == "send":
            sleep(5)
            while True:
                if len(past_broadcasts) > 63:
                    print("broadcast overflow, clearing table")
                    past_broadcasts = []
                new_broadcast_ID = const.SEARCH + random.randint(0, 63)
                if not new_broadcast_ID in past_broadcasts:
                    past_broadcasts.append(new_broadcast_ID)
                    break

            if len(other_endpoint_IDs) != 0:
                target = random.choice(other_endpoint_IDs)
            else:
                state = "listen"
                break
            #if len(past_broadcasts) == 1:
            #    message = "tag, you're it!"
            #elif len(past_broadcasts) == 2:
            #    message = "you're it again, mwahaha >:D"
            if tick <= 10:
                message = "auto-generated message " + str(tick)
                print("Auto-generated messages sent:", tick, "of 10")
                tick+=1
                bytes_to_send = (new_broadcast_ID.to_bytes(1, byteorder='big')+
                                 target.to_bytes(2, byteorder='big')+
                                 #local_ID.to_bytes(2, byteorder='big')+
                                 message.encode('utf-8'))

                for i in range(len(broadcasting_addresses)):
                    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                    soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    print("broadcast", format(new_broadcast_ID, '07b'), "on network", broadcasting_addresses[i])
                    soc.bind((broadcasting_addresses[i],0))
                    soc.sendto(bytes_to_send, (broadcasting_addresses[i], const.SERVER_PORT))
                    soc.close()
            elif not scrubbing:
                state = "scrub"
                break
            state = "listen"

        while state == "scrub":
            sleep(5)
            scrubbing = True
            while True:
                if len(past_broadcasts) > 63:
                    print("broadcast overflow, clearing table")
                    past_broadcasts = []
                new_broadcast_ID = const.SEARCH + const.SCRUB_REQ + random.randint(0, 63)
                if not new_broadcast_ID in past_broadcasts:
                    past_broadcasts.append(new_broadcast_ID)
                    break

            bytes_to_send = (new_broadcast_ID.to_bytes(1, byteorder='big') +
                             local_ID.to_bytes(2, byteorder='big'))
            for i in range(len(broadcasting_addresses)):
                soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
                soc.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                print("request", format(new_broadcast_ID, '07b'), "for scrubbing of routing data on network",
                                                                                        broadcasting_addresses[i])
                soc.bind((broadcasting_addresses[i],0))
                soc.sendto(bytes_to_send, (broadcasting_addresses[i], const.SERVER_PORT))
                soc.close()
            state = "listen"
        if state == "":
            print("Finished, resting so wireshark can remain open.")
            while True:
                x=True



if __name__ == "__main__":
    main(sys.argv[1:])