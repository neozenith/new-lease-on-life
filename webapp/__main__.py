import panel as pn
import logging


log = logging.getLogger(__name__)

# Disable tornado and bokeh loggers - only show errors
logging.getLogger("tornado").setLevel(logging.ERROR)
logging.getLogger("tornado.access").setLevel(logging.ERROR)
logging.getLogger("tornado.application").setLevel(logging.ERROR)
logging.getLogger("tornado.general").setLevel(logging.ERROR)
logging.getLogger("bokeh").setLevel(logging.ERROR)

pn.extension("deckgl", design="bootstrap", theme="dark", template="bootstrap")

from webapp.app import App

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s|%(name)s|%(levelname)s|%(filename)s:%(lineno)d - %(message)s",
    )
    log.info("Starting Isochrone Viewer")
    # Load environment variables
    app = App()

    pn.serve(app, port=5006, show=True, title="Isochrone Viewer", admin=True, threaded=True)
