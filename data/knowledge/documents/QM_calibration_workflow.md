time_of_flight
      │
resonator_spectroscopy ──▶ resonator_punchout ──▶ resonator_flux_spectroscopy
                                                         │
                         qubit_spectroscopy ◀────────────┘
                                   │
                             power_rabi (amp180)
                                   │
                             dispersive_shift
                                    │ 
                             ramsey (qubit frequency opt)     
                                    │
                  ┌──────────────────────────────────────────── ────┐
                  │                                              
                  │                                                │
             ┌──────  ─────────┐                          ┌────     ─────────┐ 
        ramsey_flux     Power Rabi State                 power          frequency
             │  (qubit opt.)     │                        │   (readout opt.)    │
             └───────┬───────────┘                        └───────┬───────────┘
                     │                                             │
                     │                                             │
                     └─────────────IQ blob. ◀───────────────────────┘
                                       │
                                       │
                                 drag_calibration 
                                       │
                               AC Stark shift 
                                        │
                              Single qubit RB
                  