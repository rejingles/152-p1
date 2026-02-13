import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
TIMEOUT = 0.2
INIT_CWND = MESSAGE_SIZE
SLOW_START = 0
AIMD = 1
FAST_RECOVERY = 2

# convert file into packets
def create_packets(filename):
    # beginning message id
    seq_id = 0

    # list of packets
    packets = {}

    # open file to be packetized
    with open(filename, 'rb') as f:
        payload = f.read(MESSAGE_SIZE)

        # split into packets
        while payload:
            # add a packet to packet list
            packets[seq_id] = seq_id.to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big') + payload
            seq_id += len(payload)
            payload = f.read(MESSAGE_SIZE)

    # empty packet to signal end of file
    packets[seq_id] = seq_id.to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big')
    return packets, seq_id

# send packets to receiver
def TCP(filename):
    # setup initial values
    cwnd = INIT_CWND
    ssthresh = 64 * MESSAGE_SIZE
    dupack = 0
    last_ack = -1

    # split file into packets and obtain final message id
    packets, final_seq = create_packets(filename)

    # create udp socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("localhost", 5002))
    udp_socket.settimeout(TIMEOUT)
    server = ("localhost", 5001)

    # next packet to be sent
    cwnd_start = 0
    next_seq = 0

    # keeping to calculate metrics
    time_sent = {}
    delays = []

    # start timer
    start = time.time()

    # we begin in slow start
    state = SLOW_START

    # send packets
    while cwnd_start < final_seq:
        # make sure we are in congestion window and it exists in packet list
        while next_seq < cwnd_start + cwnd and next_seq in packets:
            # send current packet to server
            udp_socket.sendto(packets[next_seq], server)

            # record time packet was sent
            if next_seq not in time_sent:
                time_sent[next_seq] = time.time()
            
            # next packet
            next_seq += MESSAGE_SIZE

        try:
            # check for acks
            ack_recv, _ = udp_socket.recvfrom(PACKET_SIZE)
            ack = int.from_bytes(ack_recv[:SEQ_ID_SIZE], signed=True, byteorder='big')

            # new ACK received
            if ack > cwnd_start:
                seq = cwnd_start
                while seq < ack:
                    if seq in time_sent:
                        delays.append(time.time() - time_sent[seq])
                        del time_sent[seq]
                    seq += MESSAGE_SIZE

                # shift congestion control window and start checking for duplicate ACKs
                cwnd_start = ack
                dupack = 0

                if state == SLOW_START:
                    # Slow Start
                    # increase cwnd 1 MSS per ACK
                    cwnd += MESSAGE_SIZE
                    # switch to AIMD if we reach the slow start threshold
                    if cwnd >= ssthresh:
                        state = AIMD
                elif state == AIMD:
                    # AIMD
                    # increase cwnd 1 MSS per RTT
                    cwnd += int(MESSAGE_SIZE * MESSAGE_SIZE / cwnd)
                elif state == FAST_RECOVERY:
                    # Fast Recovery
                    # immediately switch to AIMD
                    cwnd = ssthresh
                    state = AIMD

                # record ack to track dupACKs
                last_ack = ack

            # dupACK
            elif ack == last_ack:
                dupack += 1
                # fast retransmit
                if dupack == 3:
                    state = FAST_RECOVERY
                    ssthresh = max(2 * MESSAGE_SIZE, cwnd // 2)
                    cwnd = ssthresh + (3 * MESSAGE_SIZE)
                    udp_socket.sendto(packets[ack], server)
                elif dupack > 3 and state == FAST_RECOVERY:
                    cwnd += MESSAGE_SIZE
            
        except socket.timeout:
                ssthresh = max(2 * MESSAGE_SIZE, cwnd // 2)
                cwnd = INIT_CWND
                dupack = 0
                next_seq = cwnd_start
                state = SLOW_START

    # close the connection
    fin = (0).to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big') + b'==FINACK=='    
    udp_socket.sendto(fin, server)

    # end timer
    end = time.time()

    # gather data for metrics
    total_bytes = final_seq
    total_time = end - start

    # calculate return values
    throughput = total_bytes / total_time
    avg_delay = sum(delays) / len(delays)
    performance = ((0.3 * throughput) / 1000) + (0.7 / avg_delay)

    return throughput, avg_delay, performance

def main():

    throughput, delay, performance = TCP("file.mp3")

    t = round(throughput, 7)
    d = round(delay, 7)
    p = round(performance, 7)

    # print
    print("     Current Run Throughput = ", t)
    print("     Current Run Delay = ", d)
    print("     Current Run Performance Metric = ", p)

if __name__ == "__main__":
    main()