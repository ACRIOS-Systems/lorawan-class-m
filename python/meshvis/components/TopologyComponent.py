from dash import dcc, Input, Output, callback, Patch
import plotly.graph_objects as go
import networkx as nx
from .MeshDevice import MeshDevice as md
from .GraphicDefinitions import GraphicDefinitions as gDef


class TopologyComponent(dcc.Graph):

    def __init__(self):
        super().__init__(
            id='topology-component',
            style={
                'width':'100%',
                'height':'100%',
                'margin':'0px',
                'padding':'0px',
            },
            figure=self.__class__.getEmptyFigure(),
            config={
                'displaylogo': False,
                'scrollZoom':True
            }
        )

    @staticmethod
    def getEmptyFigure():
        edge_parent_trace = go.Scatter(
            x=[],
            y=[],
            line=dict(width=5, color='#F80'),
            hoverinfo='none',
            mode='lines')

        edge_child_trace = go.Scatter(
            x=[],
            y=[],
            line=dict(width=3, color='#0F0'),  # ,dash='dot'
            hoverinfo='none',
            mode='lines')

        node_trace = go.Scatter(
            x=[],
            y=[],
            mode='markers+text',
            hoverinfo='text',
            marker=dict(
                showscale=False,
                size=15,
                line_width=2))

        fig = go.Figure(
            data=[edge_parent_trace, edge_child_trace, node_trace],
            layout=go.Layout(
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=0),
                xaxis=dict(showgrid=False,
                           zeroline=False,
                           showticklabels=False),
                yaxis=dict(showgrid=False,
                           zeroline=False,
                           showticklabels=False)
            )
        )
        # User zoom etc. persists on update
        fig.update_layout(uirevision='true')
        fig.update_layout(dragmode='pan')

        return fig




    @callback(
        Output('topology-component', 'figure'),
        Input('app-store', 'data'),
        pevent_initial_call=True
    )
    def updateFigureData(n_intervals):
        G = md.getNetwork()
        pos = nx.spring_layout(G, seed=42, iterations=300, threshold=1e-7)

        edge_parent_x = []
        edge_parent_y = []
        edge_child_x = []
        edge_child_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            if edge[0].parent == edge[1]: # Check if the edge depicts parent...
                edge_parent_x.append(x0)
                edge_parent_x.append(x1)
                edge_parent_x.append(None)
                edge_parent_y.append(y0)
                edge_parent_y.append(y1)
                edge_parent_y.append(None)
            else: #... otherwise it is child connection
                edge_child_x.append(x0)
                edge_child_x.append(x1)
                edge_child_x.append(None)
                edge_child_y.append(y0)
                edge_child_y.append(y1)
                edge_child_y.append(None)
        
        node_x = []
        node_y = []
        node_color = []
        node_name = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_color.append(gDef.deviceStatusColor[node.state])
            node_name.append(node.name+"<br><br> ")
            node_text.append(node.name+"<br>"+node.eui)
            

        fig = Patch()
        fig['data'][0]['x']=edge_parent_x
        fig['data'][0]['y']=edge_parent_y
        fig['data'][1]['x']=edge_child_x
        fig['data'][1]['y']=edge_child_y
        fig['data'][2]['x']=node_x
        fig['data'][2]['y']=node_y
        fig['data'][2]['marker']['color']=node_color
        fig['data'][2]['text']=node_name
        fig['data'][2]['hovertext']=node_text
        
        return fig