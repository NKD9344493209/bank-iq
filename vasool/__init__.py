"""Bank IQ — a Regulatory Digital Twin for Indian bank customers.

The engine reads a bank statement, runs the RBI rulebook against it, and
produces findings that are deterministic, cited and explainable.

    from vasool import scan
    result = scan.scan_file("statement.csv", profile)

The rule engine decides. Language models, where used at all, only explain.
"""

__version__ = "0.7.1"
