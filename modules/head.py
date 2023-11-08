"""
This module contains the components of the config of Clash
"""


HEAD = {
    "mixed-port": 7890,
    "allow-lan": True,
    "mode": "rule",
    "log-level": "info",
    "external-controller": ":9090"
}
DNS = {
    "dns": {
        "enable": True,
        "listen": "0.0.0.0:1053",
        "default-nameserver": [
            "223.5.5.5",
            "8.8.8.8",
            "1.1.1.1"
        ],
        "nameserver": [
            "https://223.5.5.5/dns-query",
            "https://1.12.12.12/dns-query",
            "https://8.8.8.8/dns-query"
        ]
    }
}
