"""Convert an approved local probe capture into anonymized numeric fixtures."""

import argparse
import json
from pathlib import Path

READS = {
    "/ms/0/0x15": "local",
    "/ms/1/0x103/GET": "mac",
    "/ms/0/0x14": "frames",
    "/ms/0/0x7f": "moca25",
    "/ms/0/0x1003/GET": "frequency",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    reports = [
        path
        for path in sorted(args.capture.glob("*.json"))
        if path.name != "job-status.json"
    ]
    if len(reports) != 2:
        raise ValueError("Expected exactly two device capture reports")
    for label, report in zip(("adapter-a", "adapter-b"), reports, strict=True):
        original = json.loads(report.read_text())
        fixture = {"responses": {}, "net": {}, "fmr": {}}
        node = original["status_summary"]["local_node"]
        for record in original["observations"]:
            if "response" not in record:
                continue
            path, values = record["path"], list(record["response"]["data"])
            if path in READS:
                key = READS[path]
                if key == "local":
                    values = values[:13]
                elif key == "mac":
                    values = ["0x02000000", f"0x{(node + 1) << 16:08x}"]
                elif key == "frames":
                    values = ["0x00000000"] * 108
                    values[13], values[67] = "0x0001e240", "0x00039447"
                fixture["responses"][key] = values
            elif path == "/ms/0/0x16":
                peer = record["request_body"]["data"][0]
                # Keep only the MAC/version fields the decoder consumes.
                fixture["net"][str(peer)] = [
                    "0x02000000",
                    f"0x{(peer + 1) << 16:08x}",
                    "0x00000000",
                    "0x00000000",
                    values[4],
                ]
            elif path == "/ms/0/0x1D":
                mask = record["request_body"]["data"][0]
                source = mask.bit_length() - 1
                # PHY payload begins at index 10. Header identifiers are omitted.
                fixture["fmr"][str(source)] = ["0x00000000"] * 10 + values[10:34]
        (args.output / f"{label}.json").write_text(json.dumps(fixture, indent=2) + "\n")


if __name__ == "__main__":
    main()
