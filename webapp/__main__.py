import panel as pn


pn.extension('deckgl', design='bootstrap', theme='dark', template='bootstrap')

from webapp.app import App


if __name__ == "__main__":
    # Load environment variables
    app = App()
    
    pn.serve(app, port=5006, show=True, title="Isochrone Viewer", admin=True, threaded=True)