# TermChat

Minimal TCP terminal chat. Pure Python standard library — no dependencies.

## Run the server

```
python server.py --port 5555
```

Make it private (clients must know the key to join):

```
python server.py --port 5555 --key mysecret
```

## Connect a client

```
python client.py --host 127.0.0.1 --port 5555
```

If the server is private and you don't pass `--key`, you'll be prompted
for it (input hidden). You'll also be prompted for a nickname if you
don't pass `--name`.

In chat:
- `/quit` — leave
- `/list` — show who's currently online

## Notes

The private key gates entry only — traffic is plain TCP, not encrypted.
Don't reuse a sensitive password as the key.
