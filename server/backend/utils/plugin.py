import zipfile
import io

from models.plugin import Plugin
from utils.plugin_files import validate_plugin_files

def create_plugin_xpi(plugin: Plugin):
    """
    Create a .xpi file (which is just a ZIP archive) from the plugin's directory.
    """
    xpi_stream = io.BytesIO()
    files = validate_plugin_files(
        [file.model_dump() for file in plugin.get_files()]
    )
    with zipfile.ZipFile(xpi_stream, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            zipf.writestr(file["name"], file["content"])
    xpi_stream.seek(0)
    return xpi_stream.read()
