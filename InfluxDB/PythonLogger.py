# pip install pymodbus influxdb3-python
import time
from pymodbus.client import ModbusTcpClient
from influxdb_client_3 import InfluxDBClient3, Point

PLC_HOST = "127.0.0.1"
POLL_S = 1.0

plc = ModbusTcpClient(PLC_HOST, port=502)
db = InfluxDBClient3(host="http://localhost:8181",
                     token="apiv3_FhtnkJEGkCNE-NnN9iNZIA4Z_mxJMcM9kLHnwQ_3Qbsv2MfUP0UElXoQgtgXXjOASq7xaN6cZeahXfLGGKqeaA", database="MachineDB")

buffer = []   # keeps points if InfluxDB is temporarily down

def read_plc():
    # In pymodbus 3.10+ use device_id=1 instead of slave=1
    rr = plc.read_holding_registers(address=0, count=4, device_id=1)
    if rr.isError():
        raise IOError(rr)
    temp, cur, running, cycles = rr.registers
    return {
        "temperature": temp / 10.0,
        "current": cur / 10.0,
        "running": bool(running),
        "cycles": cycles,
    }

while True:
    try:
        if not plc.connected and not plc.connect():
            raise ConnectionError("PLC not reachable")

        values = read_plc()
        p = Point("motor").tag("machine", "sim_01").tag("line", "A")
        for k, v in values.items():
            p = p.field(k, v)
        buffer.append(p)

        try:
            db.write(record=buffer)
            buffer.clear()
        except Exception as e:
            print("InfluxDB write failed, buffering:", e, len(buffer))
            buffer[:] = buffer[-10000:]   # cap memory use

    except Exception as e:
        print("PLC error:", e)
        plc.close()

    time.sleep(POLL_S)