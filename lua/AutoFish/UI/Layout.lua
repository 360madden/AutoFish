local Layout = {
    window = {
        id = "autofish_root",
        title = "AutoFish",
        width = 430,
        height = 360,
    },
    sections = {
        {
            id = "status_panel",
            title = "Status",
            fields = {
                "mode",
                "activeProfile",
                "remainingBait",
                "freeSlots",
                "bridgeState",
            },
        },
        {
            id = "control_panel",
            title = "Controls",
            buttons = {
                "start",
                "pause",
                "resume",
                "stop",
                "sync_profile",
            },
        },
        {
            id = "telemetry_panel",
            title = "Telemetry",
            fields = {
                "lastAction",
                "lastReason",
                "casts",
                "hooksets",
                "catches",
                "skillUps",
                "recoveries",
                "maintenanceActions",
            },
        },
        {
            id = "alerts_panel",
            title = "Alerts",
            list = "alerts",
        },
    },
}

return Layout
