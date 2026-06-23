import os
import random
import socket

from packet_utils import (
    TYPE_ACK,
    TYPE_DATA,
    TYPE_FILE_END,
    TYPE_FILE_START,
    make_packet,
    parse_packet
)


# Receiver connection information
RECEIVER_HOST = "127.0.0.1"
RECEIVER_PORT = 5000

# Must match the sender window size
WINDOW_SIZE = 4

# Simulated packet-loss rate
LOSS_RATE = 0.3

# Maximum UDP packet size
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
    Sends an individual ACK for one sequence number.
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


def receive_file_sr():
    """
    Receives a file using the Selective Repeat protocol.
    """

    os.makedirs(RECEIVED_FOLDER, exist_ok=True)

    receiver_socket = create_receiver_socket()

    # First sequence number currently expected by the receiver window
    receive_base = 0

    # Stores packets that arrived inside the receiving window
    packet_buffer = {}

    # File information is set after FILE_START arrives
    output_file = None
    output_path = None
    expected_file_size = 0
    received_file_size = 0

    print(
        f"Selective Repeat receiver listening on "
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

            # Packet is an old duplicate that was already processed
            if seq_num < receive_base:
                print(f"Duplicate packet {seq_num}")

                send_ack(
                    receiver_socket,
                    sender_address,
                    seq_num
                )

                continue

            # Packet is beyond the current receiving window
            if seq_num >= receive_base + WINDOW_SIZE:
                print(
                    f"Packet {seq_num} is outside "
                    f"the receiving window"
                )

                continue

            # Packet is inside the receiving window
            send_ack(
                receiver_socket,
                sender_address,
                seq_num
            )

            # Store the packet if it is not already buffered
            if seq_num not in packet_buffer:
                packet_buffer[seq_num] = (
                    packet_type,
                    payload
                )

                print(f"Buffered packet {seq_num}")

            else:
                print(f"Packet {seq_num} already buffered")

            # Process consecutive buffered packets in order
            while receive_base in packet_buffer:
                buffered_type, buffered_payload = packet_buffer.pop(
                    receive_base
                )

                current_seq_num = receive_base

                if buffered_type == TYPE_FILE_START:
                    try:
                        start_information = buffered_payload.decode(
                            "utf-8"
                        )

                        file_name, file_size_text = (
                            start_information.rsplit("|", 1)
                        )

                        # Prevent the sender from choosing another folder
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

                elif buffered_type == TYPE_DATA:
                    if output_file is None:
                        print(
                            "Received DATA before a valid "
                            "FILE_START packet"
                        )

                        return

                    output_file.write(buffered_payload)
                    received_file_size += len(buffered_payload)

                    print(
                        f"Wrote packet {current_seq_num}: "
                        f"{len(buffered_payload)} bytes"
                    )

                elif buffered_type == TYPE_FILE_END:
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
                            "Warning: received file size does "
                            "not match the expected size."
                        )

                else:
                    print(
                        f"Unknown packet type: "
                        f"{buffered_type}"
                    )

                # Advance the receiving window
                receive_base += 1

                if buffered_type == TYPE_FILE_END:
                    return

    finally:
        if output_file is not None:
            output_file.close()

        receiver_socket.close()


def main():
    try:
        receive_file_sr()

    except OSError as error:
        print(f"Network or file error: {error}")


if __name__ == "__main__":
    main()