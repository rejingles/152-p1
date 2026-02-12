import socket
import time

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
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

# send packet to receiver
def stop_and_wait(filename):
    # split file into packets and obtain final message id
    packets, final_seq = create_packets(filename)

    # create udp socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("localhost", 5002))
    udp_socket.settimeout(TIMEOUT)
    server = ("localhost", 5001)

    # keeping track for metrics
    total_bytes_sent = 0
    delays = []

    # keep track of current packet
    seq_num = 0
    ack_recv = False

    # start timer
    start = time.time()

    # send packets
    while seq_num < final_seq:
        # no ack received yet
        ack_recv = False
        first_send_time = None

        while not ack_recv:
            try:
                # send current packet, record time
                udp_socket.sendto(packets[seq_num], server)
                first_send_time = time.time()
                print("Sent:", seq_num)

                # check for ack
                ack_bytes, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack = int.from_bytes(ack_bytes[:SEQ_ID_SIZE], signed=True, byteorder='big')

                # if ack received, record delay time, add to total bytes
                if ack >= seq_num:
                    ack_recv = True
                    delay = time.time() - first_send_time
                    delays.append(delay)
                    total_bytes_sent += MESSAGE_SIZE

            # if timeout, try again
            except socket.timeout:
                continue
        
        # go to next packet
        seq_num += MESSAGE_SIZE

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

    throughput, delay, performance = stop_and_wait("file.mp3")

    t = round(throughput, 7)
    d = round(delay, 7)
    p = round(performance, 7)

    # print
    print("     Current Run Throughput = ", t)
    print("     Current Run Delay = ", d)
    print("     Current Run Performance Metric = ", p)

if __name__ == "__main__":
    main()