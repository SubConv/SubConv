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
DNS_ABROAD = [
    "https://1.1.1.1/dns-query",
    "https://8.8.8.8/dns-query"
]
DNS = {
    "dns": {
        "enable": True,
        "listen": "0.0.0.0:1053",
        "default-nameserver": [
            "223.5.5.5",
            "8.8.8.8",
            "1.1.1.1"
        ],
        "nameserver-policy": {
            "geosite:gfw,geolocation-!cn": DNS_ABROAD
        },
        "nameserver": [
            "https://223.5.5.5/dns-query",
            "https://1.12.12.12/dns-query",
            "https://8.8.8.8/dns-query"
        ],
        "fallback": DNS_ABROAD,
        "fallback-filter": {
            "geoip": False,
            "geoip-code": "CN",
            "ipcidr": [
                "240.0.0.0/4"
            ]
        },
        "fake-ip-filter": [
            "+.lan",
            "+.microsoft*.com",
            "localhost.ptlogin2.qq.com"
        ]
    }
}
