from dash import dcc, Input, Output, callback
import plotly.graph_objects as go
from .MeshDevice import MeshDevice as md
from .GraphicDefinitions import GraphicDefinitions as gDef


class MapComponent(dcc.Graph):

    figure = None


    def __init__(self):

        MapComponent.updateFigure()

        super().__init__(
            id='map-component',
            style={
                'width':'100%',
                'height':'100%',
                'margin':'0px',
                'padding':'0px',
            },
            figure=MapComponent.figure,
            config={
                'displaylogo': False,
                'scrollZoom':True,
            }
        )

    
    @callback(
        Output('map-component', 'figure'),
        [Input('app-store', 'data')]
    )
    def getFigure(n_intervals):
        return MapComponent.figure


    def updateFigure():
        devices = md.getAllDevices()

        device_x = []
        device_y = []
        device_state = []
        edge_parent_x = []
        edge_parent_y = []
        edge_child_x = []
        edge_child_y = []

        devName = []
        devText = []

        for dev in devices:
            devName.append(dev.name+"<br><br> ")
            devText.append(dev.name+"<br>"+dev.eui)
            device_x.append(dev.latitude)
            device_y.append(dev.longitude)
            device_state.append(dev.state)

            if not (dev.parent is None):
                edge_parent_x.append(dev.latitude)
                edge_parent_x.append(dev.parent.latitude)
                edge_parent_x.append(None)
                edge_parent_y.append(dev.longitude)
                edge_parent_y.append(dev.parent.longitude)
                edge_parent_y.append(None)
            

            for child in dev.children: 
                edge_child_x.append(dev.latitude)
                edge_child_x.append(child.latitude)
                edge_child_x.append(None)
                edge_child_y.append(dev.longitude)
                edge_child_y.append(child.longitude)
                edge_child_y.append(None)
                
        edge_parent_trace = go.Scattermapbox(
            mode="lines",
            lat=edge_parent_x,
            lon=edge_parent_y,
            line=dict(width=5, color='#F80'),
        )
        
        edge_child_trace = go.Scattermapbox(
            mode="lines",
            lat=edge_child_x,
            lon=edge_child_y,
            line=dict(width=3, color='#0F0'),
        )

        traceDeviceOutlines = go.Scattermapbox(
            mode="markers+text",
            name="", # Prevents from showing trace name on mouse hover
            lat=device_x,
            lon=device_y,
            text=devName,
            hovertext=devText,
            marker=go.scattermapbox.Marker(
                size=19,
                color="#444444"
            ),
        )

        traceDevices = []
        for s in gDef.deviceStatusColor:
            traceDevices.append(go.Scattermapbox(
                mode="markers",
                name="", # Prevents from showing trace name on mouse hover
                lat=[device_x[i] for i in [i for i, dev in enumerate(devices) if dev.state == s]],
                lon=[device_y[i] for i in [i for i, dev in enumerate(devices) if dev.state == s]],
                text=[devText[i] for i in [i for i, dev in enumerate(devices) if dev.state == s]],
                marker=go.scattermapbox.Marker(
                    size=15,
                    color=gDef.deviceStatusColor[s]
                ),
            ))


        mapbox = go.Scattermapbox(
            mode = "markers+lines",
            lat=[],
            lon=[],
            marker=go.scattermapbox.Marker(
                size=0
            )
        )
        
        fig = go.Figure(mapbox)
        fig.add_traces([edge_parent_trace, edge_child_trace, traceDeviceOutlines, *traceDevices])
        fig.update_layout(mapbox_style="open-street-map")
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig.update_layout(mapbox_bounds={"west": -180, "east": 180, "south": -90, "north": 90})
        fig.update_traces(showlegend=False)
        fig.update_layout(uirevision='true') # User zoom etc. persists on update
        fig.update_layout(dragmode='pan')

        MapComponent.figure = fig