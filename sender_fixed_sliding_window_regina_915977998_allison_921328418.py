import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
PACKETS = {}
WINDOW_SIZE = 100 * MESSAGE_SIZE
TIMEOUT = 0.1

# convert file into packets
def create_packets(filename):
    # beginning message id
    seq_id = 0

    # open file to be packetized
    with open(filename, 'rb') as f:
        payload = f.read(MESSAGE_SIZE)

        # split into packets
        while payload:
            # add a packet to packet list
            PACKETS[seq_id] = seq_id.to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big') + payload
            seq_id += len(payload)
            payload = f.read(MESSAGE_SIZE)

    # empty packet to signal end of file
    PACKETS[seq_id] = seq_id.to_bytes(SEQ_ID_SIZE, signed=True, byteorder='big')
    return seq_id

# send packets to receiver
def sliding_window(filename):
    # split file into packets and obtain final message id
    final_seq = create_packets(filename)

    # create udp socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("localhost", 5002))
    udp_socket.settimeout(TIMEOUT)
    server = ("localhost", 5001)

    # set up window pointers
    win_start = 0   # beginning of sliding window
    next_seq = 0    # next packet to be sent

    # keeping track of time to calculate metrics
    time_sent = {}
    delays = []

    # start timer
    start = time.time()
    print("     Start time: ", start)

    # send packets
    while win_start < final_seq:
        while next_seq < win_start + WINDOW_SIZE and next_seq in PACKETS:   # make sure we are in sliding window and it exists in packet list
            # send current packet to server
            udp_socket.sendto(PACKETS[next_seq], server)
            if next_seq not in time_sent:
                time_sent[next_seq] = time.time()

            next_seq += MESSAGE_SIZE

        try:
            # check for acks
            ack_recv, _ = udp_socket.recvfrom(PACKET_SIZE)
            ack = int.from_bytes(ack_recv[:SEQ_ID_SIZE], signed=True, byteorder='big')

            if ack > win_start:
                seq = win_start
                while seq < ack:
                    if seq < ack:
                        if seq in time_sent:
                            delays.append(time.time() - time_sent[seq])
                    seq += MESSAGE_SIZE
                win_start = ack
        except socket.timeout:
            next_seq = win_start

    # close the connection    
    udp_socket.sendto(b'==FINACK==', server)

    # end timer
    end = time.time()
    print("     End time: ", end)

    # gather data for metrics
    total_bytes = final_seq
    total_time = end - start

    # calculate return values
    throughput = total_bytes / total_time
    avg_delay = sum(delays) / len(delays)
    metrics = ((0.3 * throughput) / 1000) + (0.7 / avg_delay)

    return throughput, avg_delay, metrics

def main(filename):
    throughput = []
    delay = []
    metrics = []
    for i in range(10):
        print("Run #", (i + 1))
        t, d, m = sliding_window(filename)
        print("     Throughput = ", t)
        print("     Delay = ", d)
        print("     Calculated Metrics = ", m)
        throughput.append(t)
        delay.append(d)
        metrics.append(m)

main("file.mp3")
