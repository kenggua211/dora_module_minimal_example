#!/usr/bin/env python3
"""
Sink node: receives and prints results
"""

import time
from dora import Node


def main():
    node = Node()

    for event in node:
        event_type = event["type"]

        if event_type == "INPUT":
            input_id = event["id"]

            if input_id == "result":
                value = event["value"][0].as_py()
                timestamp = time.strftime("%H:%M:%S")
                print(f"[sink] received: {value} at {timestamp}")


if __name__ == "__main__":
    main()
