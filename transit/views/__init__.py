"""Views split by feature. Names are re-exported so urls.py can keep using views.<name>."""
from .api import api_marks, api_route_buses, api_route_detail, api_routes  # noqa: F401
from .auth import signup  # noqa: F401
from .map import map_view  # noqa: F401
from .marks import (  # noqa: F401
    mark_create, mark_delete, mark_detail, mark_list, mark_update, my_marks,
)
from .routes import route_delete, route_detail, route_edit, route_list  # noqa: F401
