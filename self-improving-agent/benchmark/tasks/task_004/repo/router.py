def get_status_code(route):
    routes = {"/home": 200, "/api": 200}
    return routes.get(route, 200)
