import struct 


TYPE_FILE_START =1
TYPE_DATA =2 
TYPE_FILE_END = 3
TYPE_ACK = 4 

HEADER_FORMAT = "!BIIH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def make_packet(packet_type,seq_num=0,ack_num=0,payload=b""):
    """
    Creates one complete UDP packet consisting of a header and payload.
    """

    if not isinstance(payload, bytes):
        raise TypeError("Payload must be bytes.")

    if len(payload) > 65535:
        raise ValueError("Payload is too large.")

    header = struct.pack(
        HEADER_FORMAT,
        packet_type,
        seq_num,
        ack_num,
        len(payload)
    )

    return header + payload


def parse_packet(packet):
    """ Seperates the recived UDP into parts e.g packet_type sqn# ACK# Length """

    if len(packet) < HEADER_SIZE:
        raise ValueError("Packet is smaller than the required header.")

    packet_type, seq_num, ack_num, payload_length = struct.unpack(
        HEADER_FORMAT,
        packet[:HEADER_SIZE]
    )


    payload = packet[HEADER_SIZE:]

    if len(payload) != payload_length:
        raise ValueError("Payload length does not match the packet header.")

    return packet_type, seq_num, ack_num, payload