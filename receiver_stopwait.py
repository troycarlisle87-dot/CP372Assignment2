import os
import random
import socket

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

LOSS_RATE = 0.3
BUFFER_SIZE = 65535

# Folder where received files will be saved
RECEIVED_FOLDER = "received_files"

def create_receiver_socket():
    """
    Creates and binds the UDP receiver socket.
    """

    receiver_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    receiver_socket.bind(
        (RECEIVER_HOST, RECEIVER_PORT)
    )

    return receiver_socket

def send_ack(receiver_socket, sender_address, ack_num):
    """
    Sends an ACK for one sequence number.
    """

    ack_packet = make_packet(
        TYPE_ACK,
        ack_num=ack_num
    )

    receiver_socket.sendto(
        ack_packet,
        sender_address
    )

    print(f"Sent ACK {ack_num}")

def receive_file_stop_wait():
    """
    Receives a file using the Stop-and-Wait protocol over UDP.
    """

    os.makedirs(RECEIVED_FOLDER, exist_ok=True)

    receiver_socket = create_receiver_socket()

    expected_seq_num = 0

    output_file = None
    output_path = None
    expected_file_size = 0
    received_file_size = 0

    print(
        f"Stop-and-Wait receiver listening on "
        f"{RECEIVER_HOST}:{RECEIVER_PORT}"
    )

    print(f"Packet loss rate: {LOSS_RATE * 100:.0f}%")

    try:
        while True:
            packet, sender_address = receiver_socket.recvfrom(
                BUFFER_SIZE
            )

            # Simulate packet loss
            if random.random() < LOSS_RATE:
                print("Simulated packet loss")
                continue

            try:
                packet_type, seq_num, _, payload = parse_packet(
                    packet
                )

            except ValueError as error:
                print(f"Ignored invalid packet: {error}")
                continue

            print(
                f"Received packet {seq_num}, "
                f"type {packet_type}"
            )

            # This is the exact packet the receiver is waiting for
            if seq_num == expected_seq_num:

                send_ack(
                    receiver_socket,
                    sender_address,
                    seq_num
                )

                if packet_type == TYPE_FILE_START:
                    try:
                        start_information = payload.decode("utf-8")
                        file_name, file_size_text = (
                            start_information.rsplit("|", 1)
                        )

                        file_name = os.path.basename(file_name)
                        expected_file_size = int(file_size_text)

                    except (UnicodeDecodeError, ValueError):
                        print("Invalid FILE_START information")
                        return

                    output_path = os.path.join(
                        RECEIVED_FOLDER,
                        file_name
                    )

                    output_file = open(output_path, "wb")
                    received_file_size = 0

                    print(f"Created file: {output_path}")
                    print(
                        f"Expected file size: "
                        f"{expected_file_size} bytes"
                    )

                elif packet_type == TYPE_DATA:
                    if output_file is None:
                        print(
                            "Received DATA before a valid "
                            "FILE_START packet"
                        )
                        return

                    output_file.write(payload)
                    received_file_size += len(payload)

                    print(
                        f"Wrote packet {seq_num}: "
                        f"{len(payload)} bytes"
                    )

                elif packet_type == TYPE_FILE_END:
                    if output_file is not None:
                        output_file.close()
                        output_file = None

                    print("\nFile transfer completed.")
                    print(f"Saved file: {output_path}")
                    print(
                        f"Received size: "
                        f"{received_file_size} bytes"
                    )

                    if received_file_size == expected_file_size:
                        print("File size verified successfully.")
                    else:
                        print(
                            "Warning: received file size does not match the expected size."
                        )

                    return

                else:
                    print(f"Unknown packet type: {packet_type}")
                    return

                expected_seq_num += 1

            # Duplicate or out-of-order packet
            else:
                print(
                    f"Ignored duplicate/out-of-order packet {seq_num}. "
                    f"Expected {expected_seq_num}"
                )

                # If it is an old duplicate, ACK it again so sender can move on
                if seq_num < expected_seq_num:
                    send_ack(
                        receiver_socket,
                        sender_address,
                        seq_num
                    )

    finally:
        if output_file is not None:
            output_file.close()

        receiver_socket.close()

def main():
    try:
        receive_file_stop_wait()

    except OSError as error:
        print(f"Network or file error: {error}")


if __name__ == "__main__":
    main()
