from copy import copy
from dash import dcc, Input, Output, callback, no_update
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from .MeshPacket import MeshPacket as mp
from .MeshDevice import MeshDevice as md


class TimelineComponent(dcc.Graph):

    figure = None

    def __init__(self):

        TimelineComponent.updateFigure()

        super().__init__(
            id='timeline-component',
            style={
                'width':'100%',
                'height':'100%',
                'margin':'0px',
                'padding':'0px',
            },
            figure=TimelineComponent.figure,
            config={
                'displaylogo': False,
                'scrollZoom':True
            }
        )

    
    @callback(
        Output('timeline-component', 'figure'),
        Input('app-store', 'data')
    )
    def getFigure(n_intervals):
        return TimelineComponent.figure


    def updateFigure():
        data = pd.DataFrame()

        for p in mp.getAllPacketsAsDicts():
            if isinstance(p["data"], str):
                p["data"] = "<br><span>"+p["data"]+"</span>"
            else:
                p["data"] = "<br><span>"+"<br>".join(p["data"])+"</span>"
            data = pd.concat([data, pd.DataFrame(p, index=[1])])

        if len(data)==0:
            data = pd.DataFrame(mp.getDumbPacket().__dict__, index=[0])

        # Calculate length of packets, needed for timeline plot
        data['delta'] = data['endTime'] - data['startTime']

        # Insert column containing device names
        names = []
        for eui in data["reporterEUI"]:
            dev = md.getDeviceByEUI(eui)
            names.append(dev.name+"<br>"+dev.eui if dev else "")
        data['name'] = names

        timeline = px.timeline(
            data,
            x_start="startTime",
            x_end="endTime",
            y="name", # reporterEUI
            color="direction",
            custom_data=["data"],
            hover_data=["data"],
        )
        
        
        fig = go.Figure(timeline)
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        fig.update_layout(showlegend=False)
        fig.update_layout(yaxis_fixedrange=True)
        fig.update_layout(paper_bgcolor='rgb(229, 236, 246)')
        fig.update_layout(uirevision='true') # User zoom etc. persists on update
        fig.update_layout(dragmode='pan')
        fig.update_layout(hoverlabel_align="left")
        fig.update_xaxes(rangemode='nonnegative')
        fig.update_yaxes(ticklabeloverflow='allow')
        
        fig.update_traces(marker_line_color='rgb(0,0,0)',
                  marker_line_width=1.5, opacity=0.5)

        # Alternate background stripes
        for i in range(len(set(names))):
            if i%2==1: # Every second Y value
                fig.add_hrect(
                    y0=i-0.5,y1=i+0.5,
                    fillcolor="white",
                    opacity=0.3,
                    line_width=0,
                    layer="below"
                )
        
        # Use linear X axis, not time scale
        fig.update_layout(xaxis_type='linear')
        for d in fig.data:
            filt = data['direction'] == d.name
            d.x = data[filt]['delta'].tolist()


        TimelineComponent.figure = fig