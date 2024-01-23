
MESHOrganizationName = "organization_mesh"
MESHDeviceProfileName = "deviceProfile_mesh"
MESHApplicationName = "application_mesh"
MESHServiceProfileName = "serviceProfile_mesh"
MESHNetworkServerName = "networkServer_mesh"
MESHGatewayProfileName = "gatewayProfile_mesh"
MESHBasicChannels = [0,1,2] # use all three primary EU868 channels

MESHExtraChannels = [
      {
        "bandwidth": 125,
        "frequency": 867100000,
        "modulation": "LORA",
        "spreading_factors": [
          7,8,9,10,11,12
        ]
      },
      {
        "bandwidth": 125,
        "frequency": 867300000,
        "modulation": "LORA",
        "spreading_factors": [
          7,8,9,10,11,12
        ]
      },
      {
        "bandwidth": 125,
        "frequency": 867500000,
        "modulation": "LORA",
        "spreading_factors": [
          7,8,9,10,11,12
        ]
      },
      {
        "bandwidth": 125,
        "frequency": 867700000,
        "modulation": "LORA",
        "spreading_factors": [
          7,8,9,10,11,12
        ]
      },
      {
        "bandwidth": 125,
        "frequency": 867900000,
        "modulation": "LORA",
        "spreading_factors": [
          7,8,9,10,11,12
        ]
      }
      ]

