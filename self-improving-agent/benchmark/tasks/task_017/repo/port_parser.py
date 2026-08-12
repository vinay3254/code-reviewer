def parse_port(config):
    try:
        return int(config.get("port", "8080"))
    except KeyError:
        return 8080
