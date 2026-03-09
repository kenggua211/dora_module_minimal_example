#!/usr/bin/env python3
"""
Source node: generates incrementing integers every second
"""

import pyarrow as pa
from dora import Node


def main():
    node = Node()
    counter = 0

    for event in node:
        event_type = event["type"]

        if event_type == "INPUT":
            input_id = event["id"]

            if input_id == "tick":
                # Send incrementing number
                node.send_output(output_id="number", data=pa.array([counter]), metadata={})
                print(f"[source] sent: {counter}")
                counter += 1


if __name__ == "__main__":
    main()
