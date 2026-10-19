from device import Device
from grid import GridLayout

class SimEnvironment():
    def __init__(self, positions):
        self.layout = GridLayout(positions)
        self.device_list = []
        self._devices_by_id = {}
        self.message_FIFO = []

    def add_device(self, d):
        if d.ID not in self.layout.positions:
            raise KeyError(d.ID)
        if d.ID in self._devices_by_id:
            raise ValueError("Device ID already registered")
        self.device_list.append(d)
        self._devices_by_id[d.ID] = d
        return d

    def outgoing_message(self, msg_list, channel_ID):
        # self.message_FIFO.append({"CID": channel_ID, "MSGs": msg_list})
        self.message_FIFO += msg_list

    def get_neighbors(self, source_ID):
        if source_ID is None:
            return []
        return [self._devices_by_id[ID] for ID in self.layout.neighbors(source_ID)
                if ID in self._devices_by_id]
        
    def simulate(self, start_idx=0):
        self.device_list[start_idx].work()
        while self.message_FIFO:
            FIFO_copy = self.message_FIFO.copy()
            # handle resending
            for msg_to_send in FIFO_copy:
                neighbors = self.get_neighbors(msg_to_send.src)
                for n in neighbors:
                    n.sim_receive_broadcast(msg_to_send)

            #remove FIFO_copy from self.message_FIFO
            for spent_msg in FIFO_copy:
                self.message_FIFO.remove(spent_msg)

        for d in self.device_list:
            d.AB_protocol.new_event()

if __name__ == "__main__":
    # IDs 0-15, left to right across each row.
    positions = {y * 4 + x: (x, y) for y in range(4) for x in range(4)}
    test_env = SimEnvironment(positions)
    for device_id in positions:
        test_env.add_device(Device(device_ID=device_id, sim_tx_callback=test_env.outgoing_message))

    test_env.simulate()
