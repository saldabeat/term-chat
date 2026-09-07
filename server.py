#!/usr/bin/env python3
"""TCP terminal chat server. Broadcasts messages between connected clients.

Usage:
    python server.py [--host 0.0.0.0] [--port 5555] [--key SECRET]

If --key is given, the server is private: clients must supply the same
key before they are allowed to pick a nickname and join the chat.
"""
import argparse
import socket
import threading

lock = threading.Lock()
clients = {}  # socket -> nickname


def send_line(sock, text):
    try:
        sock.sendall((text + "\n").encode("utf-8"))
        return True
    except OSError:
        return False


def broadcast(text, exclude=None):
    with lock:
        dead = []
        for sock in clients:
            if sock is exclude:
                continue
            if not send_line(sock, text):
                dead.append(sock)
        for sock in dead:
            clients.pop(sock, None)


def read_line(fileobj):
    line = fileobj.readline()
    if not line:
        return None
    return line.rstrip("\n")


def handle_client(sock, addr, key):
    fileobj = sock.makefile("r", encoding="utf-8", newline="\n")
    nickname = None
    try:
        # Authentication
        if key:
            if not send_line(sock, "AUTH_REQUIRED"):
                return
            line = read_line(fileobj)
            if line is None or not line.startswith("KEY:"):
                return
            supplied = line[len("KEY:"):]
            if supplied != key:
                send_line(sock, "AUTH_FAIL")
                print(f"[!] {addr} rejected: bad key")
                return
            if not send_line(sock, "AUTH_OK"):
                return
        else:
            if not send_line(sock, "AUTH_OK"):
                return

        # Nickname negotiation
        while True:
            if not send_line(sock, "NICK?"):
                return
            line = read_line(fileobj)
            if line is None or not line.startswith("NICK:"):
                return
            candidate = line[len("NICK:"):].strip()
            if not candidate:
                send_line(sock, "NICK_INVALID")
                continue
            with lock:
                taken = candidate in clients.values()
                if not taken:
                    clients[sock] = candidate
                    nickname = candidate
            if taken:
                send_line(sock, "NICK_TAKEN")
                continue
            send_line(sock, "NICK_OK")
            break

        print(f"[+] {addr} joined as {nickname}")
        broadcast(f"*** {nickname} joined the chat ***", exclude=sock)

        while True:
            line = read_line(fileobj)
            if line is None:
                break
            if line == "MSG:/quit":
                break
            if line.startswith("MSG:"):
                text = line[len("MSG:"):]
                if text == "/list":
                    with lock:
                        names = ", ".join(sorted(clients.values()))
                    send_line(sock, f"*** online: {names} ***")
                    continue
                broadcast(f"MSG:{nickname}: {text}", exclude=sock)
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        pass
    finally:
        with lock:
            clients.pop(sock, None)
        try:
            sock.close()
        except OSError:
            pass
        if nickname:
            print(f"[-] {nickname} ({addr}) disconnected")
            broadcast(f"*** {nickname} left the chat ***")


def main():
    parser = argparse.ArgumentParser(description="TCP terminal chat server")
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5555, help="port to listen on (default 5555)")
    parser.add_argument("--key", default=None, help="require this private key from clients")
    args = parser.parse_args()

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((args.host, args.port))
    server_sock.listen()

    mode = "PRIVATE (key required)" if args.key else "PUBLIC"
    print(f"[*] Listening on {args.host}:{args.port} [{mode}]")

    try:
        while True:
            client_sock, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(client_sock, addr, args.key), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down")
    finally:
        server_sock.close()


if __name__ == "__main__":
    main()
