import struct
import time
import pyads
from ctypes import sizeof



AMS_NET_ID = "10.20.24.191.1.1"   # adjust to your target
PORT       = pyads.PORT_TC3PLC1   # 851
VAR_NAME   = "MAIN.arrLog"        # adjust to your variable path

N_ELEMENTS  = 11                  # ARRAY[0..10]
N_STATES    = 21                  # ARRAY[0..20]
ELEM_SIZE   = 1 + N_STATES        # 22 bytes
TOTAL_SIZE  = N_ELEMENTS * ELEM_SIZE

plc = pyads.Connection(AMS_NET_ID, PORT)
plc.open()

def parse_log(raw: bytes):
    """Convert raw bytes into a list of dicts."""
    result = []
    for i in range(N_ELEMENTS):
        chunk = raw[i * ELEM_SIZE:(i + 1) * ELEM_SIZE]
        job_id = chunk[0]
        states = list(chunk[1:])
        result.append({"nJobId": job_id, "arrState": states})
    return result

# Read the whole array as raw bytes
plc_type = pyads.PLCTYPE_BYTE * TOTAL_SIZE

@plc.notification(plc_type)
def on_change(handle, name, timestamp, value):
    print(f'type(value): {type(value)}')
    print('=' * 40)
    print(f'value: {value}')
    print('=' * 40)
    raw = bytes(value)
    data = parse_log(raw)
    print(f"[{timestamp}] {name} changed:")
    # for i, entry in enumerate(data):
    #     print(f"  [{i}] JobId={entry['nJobId']}  States={entry['arrState']}")

# Notification attributes
attr = pyads.NotificationAttrib(TOTAL_SIZE)
attr.trans_mode = pyads.ADSTRANS_SERVERONCHA   # only on change
attr.max_delay  = 100     # ms, bundle changes within 100 ms
attr.cycle_time = 50    # ms, check for changes every 50 ms

handles = plc.add_device_notification(VAR_NAME, attr, on_change)

# Initial read, since notifications only fire on a *change*
initial = plc.read_by_name(VAR_NAME, plc_type)
print("Initial value:", parse_log(bytes(initial)))

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    plc.del_device_notification(*handles)
    plc.close()