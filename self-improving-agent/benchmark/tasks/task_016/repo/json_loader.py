import json

def read_json_file(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)
