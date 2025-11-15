"""
Flask server for web dashboard with plugin extension support.
"""
from flask import Flask, Response
from typing import List, Any
import os
import socket


def find_free_port(preferred: int = 5050) -> int:
    """Try preferred port, fall back if unavailable."""
    for port in (preferred, 8080, 5000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No free port found (5050/8080/5000 busy)")


def create_app(plugins_with_web: List[Any]) -> Flask:
    """
    Create Flask app with plugin extensions.

    Args:
        plugins_with_web: List of plugin instances that provide web content
    """
    app = Flask(__name__,
                static_folder="static",
                static_url_path="")

    # Register core routes (data APIs)
    from .routes import core_routes
    core_routes.register_routes(app)

    # Register plugin routes
    for plugin in plugins_with_web:
        if hasattr(plugin, 'get_web_routes'):
            for route, handler in plugin.get_web_routes():
                app.add_url_rule(
                    route,
                    view_func=handler,
                    methods=['GET', 'POST']
                )
                print(f"Registered plugin route: {route}")

    # Main index route with plugin content injection
    @app.route("/")
    def index() -> Response: # pyright: ignore[reportUnusedFunction]
        """Serve dashboard with injected plugin content."""
        html = load_template()
        html = inject_plugin_content(html, plugins_with_web)
        return Response(html, mimetype='text/html')

    @app.route("/debug")
    def debug() -> Response:  # pyright: ignore[reportUnusedFunction]
        """Serve debug dashboard."""
        html = load_static_file("debug.html")
        return Response(html, mimetype='text/html')

    return app

def load_static_file(filename: str) -> str:
    """Load a file from the static directory."""
    file_path = os.path.join(os.path.dirname(__file__), "static", filename)
    with open(file_path, 'r') as f:
        return f.read()


def load_template() -> str:
    """Load the main dashboard HTML template."""
    return load_static_file("dashboard.html")

def inject_plugin_content(html: str, plugins: List[Any]) -> str:
    """
    Inject plugin content into dashboard HTML.

    Plugins can provide:
    - Content slots for existing sections
    - New navigation tabs
    - JavaScript for interactivity
    """
    plugin_slots: dict[str, list[str]] = {}
    plugin_js: list[str] = []
    plugin_tabs: list[dict[str, Any]] = []

    for plugin in plugins:
        if not hasattr(plugin, 'get_web_content'):
            continue

        try:
            content = plugin.get_web_content()

            # Collect slot content
            for slot_name, slot_html in content.get('slots', {}).items():
                if slot_name not in plugin_slots:
                    plugin_slots[slot_name] = []
                plugin_slots[slot_name].append(slot_html)

            # Collect JavaScript
            if content.get('javascript'):
                plugin_js.append(content['javascript'])

            # Collect new tabs
            if content.get('new_tab'):
                plugin_tabs.append(content['new_tab'])

        except Exception as e:
            print(f"Error loading plugin content: {e}")
            import traceback
            traceback.print_exc()

    # Inject slot content
    for slot_name, slot_contents in plugin_slots.items():
        slot_marker = f"<!-- CONTENT_SLOT: {slot_name} -->"
        combined_html = '\n'.join(slot_contents)
        html = html.replace(slot_marker, combined_html)

    # Inject new tabs into navigation
    if plugin_tabs:
        tab_nav_html = ''
        tab_content_html = ''

        for tab in plugin_tabs:
            tab_id = tab['id']
            tab_title = tab['title']
            tab_nav_html += f'<li><a href="#" role="button" data-tab="{tab_id}">{tab_title}</a></li>\n'
            tab_content_html += f'<section class="tab-content" id="{tab_id}">\n{tab["content"]}\n</section>\n'

        # Inject navigation items before closing </ul>
        html = html.replace('</ul>\n</nav>', f'{tab_nav_html}</ul>\n</nav>')

        # Inject content sections before closing </main>
        html = html.replace('</main>', f'{tab_content_html}</main>')

    # Inject JavaScript before closing </body>
    if plugin_js:
        combined_js = '\n\n'.join(plugin_js)
        html = html.replace('</body>', f'<script>\n// Plugin JavaScript\n{combined_js}\n</script>\n</body>')

    return html
