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
RECEIVER_HOST = "420.0.0.1"
RECEIVER_PORT = 420

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
