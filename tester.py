import socket
import random
import time
import logging

logging.basicConfig(level=logging.INFO, format='[Tester] %(message)s')

def get_random_ip():
    return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.info("Tester UDP generator started")
    while True:
        target_ip = get_random_ip()
        target_port = random.randint(1024, 65535)
        # Send a small amount of random UDP data
        data = bytes(random.getrandbits(8) for _ in range(random.randint(16, 64)))
        try:
            sock.sendto(data, (target_ip, target_port))
            logging.debug(f"Sent {len(data)} bytes to {target_ip}:{target_port}")
        except Exception as e:
            logging.debug(f"Failed to send: {e}")
        time.sleep(random.uniform(1.0, 2.0))

if __name__ == '__main__':
    main()