#!/usr/bin/env python3
"""
Node B: receives intermediate, multiplies by 2, outputs to data_out
"""

import pyarrow as pa
from dora import Node


def main():
    node = Node()

    for event in node:
        event_type = event["type"]

        if event_type == "INPUT":
            input_id = event["id"]

            if input_id == "intermediate":
                value = event["value"][0].as_py()
                result = value * 2
                node.send_output(output_id="data_out", data=pa.array([result]), metadata={})
                print(f"[node_b] {value} * 2 = {result}")


if __name__ == "__main__":
    main()
