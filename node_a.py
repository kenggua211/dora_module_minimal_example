#!/usr/bin/env python3
"""
Node A: receives data_in, adds 1, outputs to intermediate
"""

import pyarrow as pa
from dora import Node


def main():
    node = Node()

    for event in node:
        event_type = event["type"]

        if event_type == "INPUT":
            input_id = event["id"]

            if input_id == "data_in":
                value = event["value"][0].as_py()
                result = value + 1
                node.send_output(output_id="intermediate", data=pa.array([result]), metadata={})
                print(f"[node_a] {value} + 1 = {result}")


if __name__ == "__main__":
    main()
