import os 
import socket
import sys
import time 

from packet_utils import (
    TYPE_ACK,
    TYPE_DATA,
    TYPE_FILE_END,
    TYPE_FILE_START,
    make_packet,
    parse_packet
)

"""Reciever info"""
RECEIVER_HOST = "127.0.0.1"
RECEIVER_PORT = 5000

"""Repeat settings (Feel free to chagne guyus)"""
WINDOW_SIZE =4
TIMEOUT =1.0

"""File data inside each data pack"""
CHUNK_SIZE = 1024

"""Maximum UDP packet size accepted by recvform"""
BUFFER_SIZE = 65535

def read_file_chunks(file_path):

    chunks = []

    with open(file_path,"rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            chunks.append(chunk)
    return chunks 

def build_file_packets(file_path):

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    file_chunks = read_file_chunks(file_path)

    packets = []

    start_information = f"{file_name}|{file_size}".encode("utf-8")
    packets.append(
        make_packet(
            TYPE_FILE_START,
            seq_num=0,
            payload=start_information
        )
    )
    sequence_number =1

    for chunk in file_chunks:
        packets.append(
            make_packet(
                TYPE_DATA,
                seq_num=sequence_number,
                payload=chunk
            )
        )
        sequence_number+=1
    packets.append(
        make_packet(
            TYPE_FILE_END,
            seq_num=sequence_number
        )
    )
    return packets

def send_file_sr(file_path):
    """Sends the file using the Selective repeat style
    
    """
    packets = build_file_packets(file_path)
    total_packets = len(packets)

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_socket.settimeout(0.1)

    receiver_address = (RECEIVER_HOST,RECEIVER_PORT)

    # First packet hence the name base
    base=0

    #Next packet hence next, totally not stolen from 164 formatting
    next_seq_num =0

    #Tracks wether each packet has been acknowledged
    acknowledged = [False] * total_packets

    #Stores the last transmission time of each packet
    send_times ={}

    #Measurement metrics 
    retransmissions =0
    transfer_start_time = time.time()

    #Rubber ducky method
    print(f"Sending: {file_path}")
    print(f"Total packets: {total_packets}")
    print(f"Window size: {WINDOW_SIZE}")
    try:
        while base < total_packets:

            # send the new packets that are allowed for this windopw 
            while (
                next_seq_num < total_packets
                and next_seq_num < base + WINDOW_SIZE
            ):
                sender_socket.sendto(
                    packets[next_seq_num],
                    receiver_address
                )

                send_times[next_seq_num] = time.monotonic()

                print(f"Sent packet {next_seq_num}")

                next_seq_num +=1
            #Receive and process an ACK
            try:
                response, _ = sender_socket.recvfrom(BUFFER_SIZE)

                packet_type,_, ack_num, _ = parse_packet(response)

                if (packet_type == TYPE_ACK and 0 <=ack_num<total_packets):
                    if not acknowledged[ack_num]:
                        acknowledged[ack_num]= True
                        send_times.pop(ack_num, None)

                        print(f"Received ACK {ack_num}")
                    while( base<total_packets and acknowledged[base]):
                        base+=1
            except socket.timeout:
                pass
            except ValueError as error:
                print("Ingored ack it was invalid: {error}")
            
            # 3rd logic bracket to check for outstanding packets timeouts
            current_time = time.monotonic()

            for seq_num in range(base, next_seq_num):
                if acknowledged[seq_num]:
                    continue
                elapsed_time = current_time - send_times[seq_num]

                if elapsed_time >= TIMEOUT:
                    sender_socket.sendto(
                        packets[seq_num],
                        receiver_address
                    )
                    send_times[seq_num] = time.monotonic()
                    retransmissions +=1

                    
                    print(f"Timeout: resent packet {seq_num}")
        transfer_end_time = time.time()
        transfer_time = transfer_end_time - transfer_start_time

        file_size = os.path.getsize(file_path)

        if transfer_time >0:
            throughput = file_size / transfer_time
        else:
            throughput = 0
        print("\nFile transfer completed")
        print(f"Transfer time: {transfer_time:.4f} Seconds")
        print(f"Throughput: {throughput:.2f} btyes/second")
        print(f"Retransmissions: {retransmissions}")

        return transfer_time, throughput,retransmissions
    finally: 
        sender_socket.close()

# Youre not gonna believe me when I tell you what this does
def main():
    if len(sys.argv) != 2:
        print("Usage: python sender_sr.py <file_path>")
        return
    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return
    try:
        send_file_sr(file_path)
    except OSError as error:
        print(f"Network or file error: {error}")
if __name__ == "__main__":
    main()