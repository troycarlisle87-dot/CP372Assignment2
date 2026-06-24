import socket
import os
import sys
import time

# packet format
from packet_utils import (
    TYPE_ACK,
    TYPE_DATA,
    TYPE_FILE_END,
    TYPE_FILE_START,
    make_packet,
    parse_packet
)

# reciever info
RECEIVER_HOST = "127.0.0.1"
RECEIVER_PORT = 5000

CHUNK_SIZE = 1024
TIMEOUT = 1
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

def send_packet_stop_wait(sender_socket, packet, packet_num, receiver_address):
    """
    Sends one packet and waits for ACK. 
    If timeout occurs, the packet is retransmitted.
    """

    retransmissions = 0

    while True:
        sender_socket.sendto(packet, receiver_address)
        print(f"Sent packet {packet_num}")

        try:
            response, _ = sender_socket.recvfrom(BUFFER_SIZE)

            packet_type, _, ack_num, _ = parse_packet(response)

            # ensure ACK matches
            if packet_type == TYPE_ACK and ack_num == packet_num:
                print(f"Received ACK {ack_num}")
                return retransmissions

            print(f"Ignored unexpected ACK {ack_num}")

        except socket.timeout:
            retransmissions += 1
            print(f"Timeout: resent packet {packet_num}")

        except ValueError as error:
            print(f"Ignored invalid ACK: {error}")

def send_file_stop_wait(file_path):
    """
    Sends a file using the Stop-and-Wait protocol over UDP.
    """

    packets = build_file_packets(file_path)
    total_packets = len(packets)

    sender_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender_socket.settimeout(TIMEOUT)

    receiver_address = (RECEIVER_HOST, RECEIVER_PORT)

    retransmissions = 0
    transfer_start_time = time.time()

    print(f"Sending: {file_path}")
    print(f"Total packets: {total_packets}")

    try:
        for packet_index, packet in enumerate(packets):
            retransmissions += send_packet_stop_wait(
                sender_socket,
                packet,
                packet_index,
                receiver_address
            )

        transfer_end_time = time.time()
        transfer_time = transfer_end_time - transfer_start_time

        file_size = os.path.getsize(file_path)

        if transfer_time > 0:
            throughput = file_size / transfer_time
        else:
            throughput = 0

        print("\nFile transfer completed")
        print(f"Transfer time: {transfer_time:.4f} seconds")
        print(f"Throughput: {throughput:.2f} bytes/second")
        print(f"Retransmissions: {retransmissions}")

        return transfer_time, throughput, retransmissions

    finally:
        sender_socket.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python sender_stopwait.py <file_path>")
        return

    file_path = sys.argv[1]

    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        send_file_stop_wait(file_path)

    except OSError as error:
        print(f"Network or file error: {error}")

if __name__ == "__main__":
    main()
