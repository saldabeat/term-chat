#!/usr/bin/env python3
"""TCP terminal chat client.

Usage:
    python client.py --host 127.0.0.1 --port 5555 [--key SECRET] [--name YOURNAME]

If the server is private and --key is not given, you will be prompted
for it (input hidden). Type /quit to leave, /list to see who's online.
"""
import argparse
import getpass
import socket
import sys
import threading

running = True


def read_line(fileobj):
    line = fileobj.readline()
    if not line:
        return None
    return line.rstrip("\n")


def receiver(sock, fileobj):
    global running
    while running:
        line = read_line(fileobj)
        if line is None:
            print("\n[!] Disconnected from server")
            running = False
            break
        if line.startswith("MSG:"):
            print(line[len("MSG:"):])
        else:
            print(line)


def main():
    parser = argparse.ArgumentParser(description="TCP terminal chat client")
    parser.add_argument("--host", default="127.0.0.1", help="server address")
    parser.add_argument("--port", type=int, default=5555, help="server port")
    parser.add_argument("--key", default=None, help="private key (omit to be prompted if needed)")
    parser.add_argument("--name", default=None, help="nickname (omit to be prompted)")
    args = parser.parse_args()

    global running

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((args.host, args.port))
    except OSError as e:
        print(f"[!] Could not connect to {args.host}:{args.port}: {e}")
        sys.exit(1)

    fileobj = sock.makefile("r", encoding="utf-8", newline="\n")

    line = read_line(fileobj)
    if line == "AUTH_REQUIRED":
        key = args.key or getpass.getpass("Enter private key: ")
        sock.sendall(f"KEY:{key}\n".encode("utf-8"))
        resp = read_line(fileobj)
        if resp != "AUTH_OK":
            print("[!] Rejected: invalid private key")
            sock.close()
            sys.exit(1)
    elif line != "AUTH_OK":
        print("[!] Unexpected response from server")
        sock.close()
        sys.exit(1)

    while True:
        prompt_line = read_line(fileobj)
        if prompt_line != "NICK?":
            print("[!] Unexpected response from server")
            sock.close()
            sys.exit(1)
        name = args.name or input("Choose a nickname: ")
        args.name = None  # force re-prompt if taken
        sock.sendall(f"NICK:{name}\n".encode("utf-8"))
        resp = read_line(fileobj)
        if resp == "NICK_OK":
            break
        elif resp == "NICK_TAKEN":
            print("[!] That nickname is taken, try another.")
        elif resp == "NICK_INVALID":
            print("[!] Nickname cannot be empty.")
        else:
            print("[!] Unexpected response from server")
            sock.close()
            sys.exit(1)

    print(f"[*] Connected as {name}. Type /quit to leave, /list to see who's online.")

    t = threading.Thread(target=receiver, args=(sock, fileobj), daemon=True)
    t.start()

    try:
        while running:
            try:
                text = input()
            except EOFError:
                text = "/quit"
            if not running:
                break
            sock.sendall(f"MSG:{text}\n".encode("utf-8"))
            if text == "/quit":
                break
    except KeyboardInterrupt:
        try:
            sock.sendall(b"MSG:/quit\n")
        except OSError:
            pass
    finally:
        running = False
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
