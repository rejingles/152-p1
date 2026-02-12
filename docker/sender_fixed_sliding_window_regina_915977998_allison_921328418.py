import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
WINDOW_SIZE = 20 * MESSAGE_SIZE
TIMEOUT = 0.1

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
def sliding_window(filename):
    # split file into packets and obtain final message id
    packets, final_seq = create_packets(filename)

    # create udp socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("localhost", 5002))
    udp_socket.settimeout(TIMEOUT)
    server = ("localhost", 5001)

    # set up window pointers
    win_start = 0   # beginning of sliding window
    next_seq = 0    # next packet to be sent

    # keeping to calculate metrics
    time_sent = {}
    delays = []

    # start timer
    start = time.time()

    # send packets
    while win_start < final_seq:
        # make sure we are in sliding window and it exists in packet list
        while next_seq < win_start + WINDOW_SIZE and next_seq in packets:
            # send current packet to server
            udp_socket.sendto(packets[next_seq], server)
            print("Sent: ", next_seq) #debug

            # record time packet was sent
            if next_seq not in time_sent:
                time_sent[next_seq] = time.time()
            
            # next packet
            next_seq += MESSAGE_SIZE

        try:
            # check for acks
            ack_recv, _ = udp_socket.recvfrom(PACKET_SIZE)
            ack = int.from_bytes(ack_recv[:SEQ_ID_SIZE], signed=True, byteorder='big')

            # shift sliding window
            if ack > win_start:
                seq = win_start
                # calculate delay if packets are sent out of order
                while seq < ack:
                    if seq < ack:
                        if seq in time_sent:
                            delays.append(time.time() - time_sent[seq])
                    seq += MESSAGE_SIZE
                # shift window after receiving first in order packet
                win_start = ack
        # timeout
        except socket.timeout:
            # resend lost packets
            next_seq = win_start

    # close the connection
    fin = (0).to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big') + b'==FINACK=='    
    udp_socket.sendto(fin, server)

    # end timer
    end = time.time()

    # gather data for metrics
    total_bytes = final_seq
    total_time = end - start
    print(total_time)

    # calculate return values
    throughput = total_bytes / total_time
    avg_delay = sum(delays) / len(delays)
    performance = ((0.3 * throughput) / 1000) + (0.7 / avg_delay)

    return throughput, avg_delay, performance

def main():

    throughput, delay, performance = sliding_window("file.mp3")

    t = round(throughput, 7)
    d = round(delay, 7)
    p = round(performance, 7)

    # print
    print("     Current Run Throughput = ", t)
    print("     Current Run Delay = ", d)
    print("     Current Run Performance Metric = ", p)

if __name__ == "__main__":
    main()