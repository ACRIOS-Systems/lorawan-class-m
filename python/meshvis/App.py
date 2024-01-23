# Plotly v2.25.2
from dash import Dash, html, dcc, Input, Output, callback
from threading import Thread
import argparse

from components.DataInterface import DataInterface

from components.MapComponent import MapComponent
from components.TopologyComponent import TopologyComponent
from components.TimelineComponent import TimelineComponent

from components.MeshDevice import MeshDevice as md
from components.MeshPacket import MeshPacket as mp


class App(Dash):

    def __init__(self, debug=False, noResetButtons=False):
        super().__init__(
            "MeshVis",
            title='MeshVis',
            update_title=None,
            external_scripts=['https://cdnjs.cloudflare.com/ajax/libs/split.js/1.6.5/split.min.js'],
            url_base_pathname="/meshvis/"
        )

        topologyComponent = TopologyComponent()
        mapComponent = MapComponent()
        timelineComponent = TimelineComponent()

        debugMenu = html.Div(id='debug-menu-content', children=[
            html.Button('DEBUG: New random device', id='btn-new-dev', n_clicks=0),
            html.Br(),
            html.Button('DEBUG: New random packet', id='btn-new-pkt', n_clicks=0),
        ])
        

        self.layout = html.Div(id='app', children=[
            dcc.Interval(
                id='refresh-component',
                interval=1000,
                n_intervals=0,
                disabled=False
            ),
            html.Div(id='black-hole', style={'display':'none'}),
            dcc.Store(id='app-store', data=0),
            html.Div(id='app-menu-bar', children=[
                html.Div(id='app-menu-content', children=[
                    html.H3("Menu"),
                    # MENU ITEMS
                    html.Fieldset(
                        children=[
                            html.Legend(
                                children="Auto-refresh"
                            ),
                            dcc.Checklist(
                                id="refresh-checkbox",
                                options=[{"label": " ms:", "value": "enabled"}],
                                value=["enabled"] # Ticked by default
                            ),
                            dcc.Input(
                                id="refresh-period",
                                type='number',
                                placeholder='Refresh period',
                                value=1000,
                                min=100,
                                max=60000,
                            )
                        ]
                    ),
                    html.Br(),
                    html.Fieldset(
                        children=[
                            html.Legend(
                                children="Data reset"
                            ),
                        dcc.ConfirmDialogProvider(
                            children=html.Button('Delete all devices', id='btn-del-dev', n_clicks=0),
                            id='del-dev-dialog',
                            message='Are you sure you want to delete all devices from the server?'
                        ),
                        dcc.ConfirmDialogProvider(
                            children=html.Button('Delete all packets', id='btn-del-pkt', n_clicks=0),
                            id='del-pkt-dialog',
                            message='Are you sure you want to delete all packets from the server?'
                        ),
                    ]) if not noResetButtons else None,
                    html.Div(id='debug-menu-flex') if debug else None,
                    debugMenu if debug else None,
                ]),
                html.Div(id='app-menu-button'),
            ]),
            html.Div(id='app-window', className='', children=[
                html.Div(id='app-window-top', className='', children=[
                    html.Div(id='app-window-top-left', className='app-windows', children=[
                        topologyComponent
                    ]),
                    html.Div(id='app-window-top-right', className='app-windows', children=[
                        mapComponent
                    ]),
                ]),
                html.Div(id='app-window-bottom', className='app-windows', children=[
                    timelineComponent
                ]),
            ]),
        ])

        # The auto-refresh checkbox and input clientside callbacks
        self.clientside_callback(
            """
            function(value) {
                try {
                    return !value.includes('enabled');
                } catch (error) {
                    return null;
                }
            }
            """,
            Output('refresh-component', 'disabled'),
            Input('refresh-checkbox', 'value'),
        
        )
        self.clientside_callback(
            """
            function(value) {
                try {
                    return value;
                } catch (error) {
                    return 1000;
                }
            }
            """,
            Output('refresh-component', 'interval'),
            Input('refresh-period', 'value'),
        
        )

        # Interval to Store callback
        self.clientside_callback(
            """
            function(n_intervals) {
                if(isMouseDown) {
                    return dash_clientside.no_update;
                } else {
                    return n_intervals;
                }
            }
            """,
            Output('app-store', 'data'),
            Input('refresh-component', 'n_intervals'),
            prevent_initial_call=True
        )


        # DEBUG: Add new random dummy device button
        @callback(
            Output('black-hole', 'children', allow_duplicate=True),
            Input('btn-new-dev', 'n_clicks'),
            prevent_initial_call=True
        )
        def newDevBtnCallback(n_clicks):
            md.newExampleDevice()
            return ''

        # DEBUG: Add new random packet button
        @callback(
            Output('black-hole', 'children', allow_duplicate=True),
            Input('btn-new-pkt', 'n_clicks'),
            prevent_initial_call=True
        )
        def newPktBtnCallback(n_clicks):
            mp.newExamplePacket()
            return ''

        if not noResetButtons:
            # Delete all devices and packets buttons
            @callback(
                Output('black-hole', 'children', allow_duplicate=True),
                Input('del-dev-dialog', 'submit_n_clicks'),
                prevent_initial_call=True,
            )
            def delDevBtnCallback(submit_n_clicks):
                md.deviceList = []
                return ''

            @callback(
                Output('black-hole', 'children', allow_duplicate=True),
                Input('del-pkt-dialog', 'submit_n_clicks'),
                prevent_initial_call=True,
            )
            def delPktBtnCallback(submit_n_clicks):
                mp.packetList = []
                return ''


if __name__ == '__main__':
    # Process CLI arguments...
    parser = argparse.ArgumentParser(description='MeshVis', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-p', '--port', type=int, metavar='port-number', default='8050', help='TCP listening port number')
    parser.add_argument('-d', '--debug', action='store_true', help='Run the MeshVis with debug options on')
    parser.add_argument('--no-data-reset-buttons', action='store_true', help='Hide the Data reset buttons in the menu')
    args = parser.parse_args()

    # Init. the web application
    app = App(debug=args.debug, noResetButtons=args.no_data_reset_buttons)
    
    # Init the JSON API
    DataInterface(app.server)

    # Redirect / to /meshvis automatically
    @app.server.route('/', methods=['GET'])
    def redirect():
        return app.server.redirect("/meshvis", code=302)

    # If not debugging, only allow warnings to be printed to the console
    if not args.debug:
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)

    # Start the application
    app.run_server(host="0.0.0.0", port=args.port, debug=args.debug, dev_tools_hot_reload=False, use_reloader=False)