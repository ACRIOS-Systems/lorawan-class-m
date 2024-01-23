import re
import csv
import prettytable as pt

import tkinter as tk
from tkinter import filedialog as fd
from tkinter import messagebox as mb
import tkintermapview as tkmap

import GUIDevice as gd


class DeviceSetup(tk.Tk):

    tilesets = {
        "OpenStreetMap"    : {"max_zoom": 19, "URL": "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"},
        "Google normal"    : {"max_zoom": 22, "URL": "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Ga"},
        "Google satellite" : {"max_zoom": 22, "URL": "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga"},
        "Stamen painting"  : {"max_zoom": 19, "URL": "http://c.tile.stamen.com/watercolor/{z}/{x}/{y}.png"},
        "Stamen B&W"       : {"max_zoom": 19, "URL": "http://a.tile.stamen.com/toner/{z}/{x}/{y}.png"},
    }


    def run(self):
        self.mainloop()


    def newFile(self):
        for dev in gd.deviceList.copy():
            dev.marker.delete()
            gd.deviceList.remove(dev)
            self.refreshDevices()
            self.fillConfigTable(None)
        
        return True


    @staticmethod
    def __parseLine(head, line) -> dict:
        if len(line) == 0:
            return None

        ret = dict()
        for i in range(len(head)):
            ret[head[i]] = line[i]
        else:
            return ret

    @staticmethod
    def __stripSpaces(line):
        for i in range(len(line)):
            line[i] = line[i].strip()
        return line

    def loadFile(self):
        file = fd.askopenfile(mode="r", filetypes=[("CSV files", ["*.csv", "*.CSV", "*.Csv"])])
        if file is None:
            return False
        
        with open(file.name, "r") as f:
            reader = csv.reader(f)
            header = self.__stripSpaces(next(reader, None))

            # Check if the header is of a correct format
            if not set(header)==set(gd.GUIDevice.deviceParameters):
                print("The opened CSV file does not contain correct header!")
                print("Should not contain:")
                print(set(header)-set(gd.GUIDevice.deviceParameters))
                print("Does not contain:")
                print(set(gd.GUIDevice.deviceParameters)-set(header))
                mb.showerror("File format error", "The opened CSV file does not contain correct header!")
                return False

            # Clean all data before loading the new ones
            self.newFile()

            while (line := next(reader, None)):
                line = self.__stripSpaces(line)
                cfg = self.__parseLine(header, line)

                cfg["latitude"] = float(cfg["latitude"])
                cfg["longitude"] = float(cfg["longitude"])
                cfg["altitude"] = float(cfg["altitude"])
                
                # Create a new map marker for the new device
                marker = self.map.set_marker(cfg["latitude"], cfg["longitude"], cfg["name"])

                # Create the device and append it to the device list
                newDev = gd.GUIDevice(cfg["name"], cfg["latitude"], cfg["longitude"], marker, params=cfg)
                gd.deviceList.append(newDev)

                # Colorize marker to blue if the device is a gateway
                if newDev.params["type"].lower()=="gateway":
                    self.modifyMarker(newDev.marker, name=newDev.name, color="blue")

            self.refreshDevices()

            return True
                


    def saveFile(self):
        file = fd.asksaveasfile(mode="w", filetypes=[("CSV file", ["*.csv"])])
        if file is None:
            return False

        table = pt.PrettyTable(field_names=gd.GUIDevice.deviceParameters)
        # Format to CSV
        table.border = False
        table.align = "l"
        table.preserve_internal_border = True
        table.right_padding_width = 1
        table.left_padding_width = 0
        table.vertical_char = ","
        table.hrules = pt.NONE

        for dev in gd.deviceList:
            table.add_row(['"'+str(dev.params[p])+'"' for p in gd.GUIDevice.deviceParameters])

        string = table.get_formatted_string()

        with open(file.name, mode="w") as f:
            f.write(string)

        return True


    def __init__(self):
        super().__init__()

        self.title("LoRa Radio Sim scenario setup tool")

        self.deviceParamValues = {}
        
        # Default and minimum window size
        #self.geometry(f"{800}x{600}") # Not needed, window size defined by the map widget
        self.minsize(400, 200)


        #         Paned windows
        # ┌────────────────────────────┐
        # │          mainPane          │
        # │ ┌────────────┐  ┌────────┐ │
        # │ │  leftPane  │  │        │ │
        # | |(devDelBtn) |  |        | |
        # │ │ ┌───────┬┐ │  │        │ │
        # │ │ │devList││ │  │        │ │
        # │ │ │ Pane  ││ │  │        │ │
        # │ │ └───────┴┘ │  │        │ │
        # │ │            │  │self.map│ │
        # │ │ ┌───────┬┐ │  │        │ │
        # │ │ │DevOpts││ │  │        │ │
        # │ │ │ Pane  ││ │  │        │ │
        # │ │ └───────┴┘ │  │        │ │
        # │ └────────────┘  └────────┘ │
        # └────────────────────────────┘
        #
        mainPane = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        mainPane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        leftPane = tk.PanedWindow(mainPane, orient=tk.VERTICAL, sashwidth=0)
        mainPane.add(leftPane)

        devDelBtn = tk.Button(leftPane, text="Delete device(s)", command=self.deleteSelectedDevice)
        leftPane.add(devDelBtn)

        devUpBtn = tk.Button(leftPane, text="Move device up", command=self.upSelectedDevice)
        leftPane.add(devUpBtn)

        devDownBtn = tk.Button(leftPane, text="Move device down", command=self.downSelectedDevice)
        leftPane.add(devDownBtn)

        devListPane = tk.PanedWindow(leftPane, orient=tk.HORIZONTAL, sashwidth=0)
        leftPane.add(devListPane)

        devOptsPane = tk.PanedWindow(leftPane, orient=tk.VERTICAL, sashwidth=0)
        leftPane.add(devOptsPane)
        leftPane.paneconfig(devListPane, stretch="always")


        ### Device list
        self.devList = tk.Listbox(devListPane, activestyle="dotbox", highlightthickness=0, exportselection = False) # exportselection=False keeps a selected item selected when clicking anywhere else
        devListPane.add(self.devList, stretch="always")
        self.devList.bind('<<ListboxSelect>>', self.onDeviceSelection)
        # Scrollbar for the list
        devListScrollbar = tk.Scrollbar(devListPane)
        devListPane.add(devListScrollbar, stretch="never")
        # Link the scrollbar to the list
        self.devList.config(yscrollcommand=devListScrollbar.set)
        devListScrollbar.config(command=self.devList.yview)


        ### Device config menu
        def onParamUpdate(param, value):
            idx = self.devList.curselection()
            if len(idx)==0: # if no device is selected in the list
                if value=="":
                    return True
                else:
                    return False
            if param in ["latitude", "longitude", "altitude", "startDelay"]: # if the value is not numeric when required
                if not re.match('^[0-9\.\ \-]*$', value):
                    return False
                if not value.removeprefix('-').replace('.','',1).isdigit():
                    return False

            name = self.devList.get(idx)
            device = gd.GUIDevice.getDeviceByName(name)

            if param=="name":
                d = gd.GUIDevice.getDeviceByName(value)
                # if device with the same name already exists, do not allow another one to be named the same
                if not d is None:
                    if not device is d:
                        return False

            device.updateParam(param, value)
            if param=="name": # if name was changed, use the new value for final reselection in the devList
                name = value
            self.refreshDevices()
            self.devList.select_set(idx)
            self.onDeviceSelection(event="redraw")
            return True
        paramUpdateFunc = self.register(onParamUpdate)

        for i, labelText in enumerate(gd.GUIDevice.deviceParameters):
            row = tk.PanedWindow(devOptsPane, orient=tk.HORIZONTAL, height=15, sashwidth=0)
            label = tk.Label(row, text=labelText, width=12, justify="right")
            self.deviceParamValues[labelText] = tk.StringVar()
            value = tk.Entry(row, textvariable=self.deviceParamValues[labelText], validate="all", validatecommand=(paramUpdateFunc, labelText, "%P"))
            label.grid(row=i, column=0, padx=5, pady=5, sticky="w")
            value.insert(0, "")
            value.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            
            row.add(label)
            row.add(value)
            devOptsPane.add(row)
            devOptsPane.paneconfig(row, minsize=1.5*row.winfo_reqheight(), stretch="never")

        leftPane.paneconfig(devOptsPane, stretch="never")



        ### Map
        self.map = tkmap.TkinterMapView(mainPane, width=800, height=600, corner_radius=0)
        mainPane.add(self.map)
        self.map.set_position(49.1938951, 16.6091053) # Default map center to Brno, Czech republic
        self.map.set_zoom(12)
        # Context menu
        self.map.add_right_click_menu_command(label="Add device here",
                                        command=self.newDevice,
                                        pass_coords=True)
        self.map.add_right_click_menu_command(label="Move device here",
                                        command=self.moveDevice,
                                        pass_coords=True)

        # Top menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File submenu
        fileMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=fileMenu)
        fileMenu.add_command(label="New", command=self.newFile)
        fileMenu.add_command(label="Load", command=self.loadFile)
        fileMenu.add_command(label="Save as", command=self.saveFile)
        fileMenu.add_separator()
        fileMenu.add_command(label="Exit", command=self.quit)
        
        # Map submenu
        mapMenu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Map", menu=mapMenu)
        #mapMenu.add_command(label="Refresh", command=self.map.update_canvas_tile_images())
        #mapMenu.add_separator()
        for tsName in self.__class__.tilesets:
            ts = self.__class__.tilesets[tsName]
            mapMenu.add_command(label=tsName, command=
                lambda ts=ts: self.map.set_tile_server(tile_server=ts['URL'], max_zoom=ts["max_zoom"])
            )

        # DEBUG submenu
        if True:
            debugMenu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="DEBUG", menu=debugMenu)
            debugMenu.add_command(label="Print current tile server URL", command=lambda: print(self.map.tile_server))

    
    @staticmethod
    def modifyMarker(marker, name=None, color:str="red", position=None):
        if not name is None:
            marker.text = name

        if color.lower()=="blue":
            marker.marker_color_circle = '#261E9B'
            marker.marker_color_outside = '#542DC5'
            marker.text_color = '#2A2265'
        elif color.lower()=="green":
            marker.marker_color_circle = '#269B1E'
            marker.marker_color_outside = '#54C52D'
            marker.text_color = '#2A6522'
        else: # red
            marker.marker_color_circle = '#9B261E'
            marker.marker_color_outside = '#C5542D'
            marker.text_color = '#652A22'
        
        # Force redraw of the marker by moving it out of bounds and back
        if position is None:
            coord = marker.position
        else:
            coord = position
        marker.position = (1e9, 1e9)
        marker.draw()
        marker.position = coord
        marker.draw()


    def onDeviceSelection(self, event):
        listbox = self.devList
        if len(listbox.curselection())==0:
            return
        name = listbox.get(*listbox.curselection())
        device = gd.GUIDevice.getDeviceByName(name)
        if not event=="redraw":
            self.fillConfigTable(device)
        # Redraw markers
        for dev in gd.deviceList:
            if name==dev.name:
                self.modifyMarker(dev.marker, name=dev.name, color="green", position=(float(dev.params["latitude"]), float(dev.params["longitude"])))
            else:
                if dev.params["type"].lower()=="gateway":
                    self.modifyMarker(dev.marker, name=dev.name, color="blue", position=(float(dev.params["latitude"]), float(dev.params["longitude"])))
                else:
                    self.modifyMarker(dev.marker, name=dev.name, color="red", position=(float(dev.params["latitude"]), float(dev.params["longitude"])))


    def deleteSelectedDevice(self):
        idx = self.devList.curselection()
        if len(idx)==0:
            return
        name = self.devList.get(idx)
        dev = gd.GUIDevice.getDeviceByName(name)
        dev.marker.delete()
        gd.deviceList.remove(dev)
        self.refreshDevices()
        self.fillConfigTable(None)

    
    def upSelectedDevice(self):
        idx = self.devList.curselection()
        if 0 in idx or len(idx)==0:
            return
        idx = idx[0]
        swap = gd.deviceList[idx]
        gd.deviceList[idx] = gd.deviceList[idx-1]
        gd.deviceList[idx-1] = swap
        self.refreshDevices()
        self.devList.select_set(idx-1)

    
    def downSelectedDevice(self):
        idx = self.devList.curselection()
        if (len(gd.deviceList)-1) in idx or len(idx)==0:
            return
        idx = idx[0]
        swap = gd.deviceList[idx]
        gd.deviceList[idx] = gd.deviceList[idx+1]
        gd.deviceList[idx+1] = swap
        self.refreshDevices()
        self.devList.select_set(idx+1)

    
    def fillConfigTable(self, device: gd.GUIDevice):
        for p in gd.GUIDevice.deviceParameters:
            entry = self.deviceParamValues[p] # type: tk.StringVar
            if device is None:
                entry.set("")
            else:
                entry.set(device.params[p])


    def refreshDevices(self):
        self.devList.delete(0, 'end')

        devList = gd.deviceList # type: list[gd.GUIDevice]
        for dev in devList:
            self.devList.insert('end', dev.name)
            

    def newDevice(self, coords):
        # Derive the default device name
        default_name = "Device"
        number = 0
        name = f"{default_name}{number:02}" # Format the name
        # Check if the new name already exists in the device list
        devList = gd.deviceList # type: list[gd.GUIDevice]
        while any(dev.name == name for dev in devList):
            number += 1
            name = f"{default_name}{number:02}" # Increment the number and update the name

        # Create a new map marker for the new device
        marker = self.map.set_marker(*coords, text=name)

        # Create the device and append it to the device list
        newDev = gd.GUIDevice(name, *coords, marker)
        gd.deviceList.append(newDev)

        self.refreshDevices()

    
    def moveDevice(self, coords):
        # Get selected device
        idx = self.devList.curselection()
        if len(idx)==0:
            mb.showerror("Error", "No device selected.")
            return
        idx = idx[0]
        dev = gd.deviceList[idx] # type: gd.GUIDevice

        dev.updateParam("latitude", coords[0])
        dev.updateParam("longitude", coords[1])
        DeviceSetup.modifyMarker(marker=dev.marker, color="green", position=coords)
        DeviceSetup.fillConfigTable(self, dev)


if __name__ == "__main__":
    window = DeviceSetup()    
    window.run()