from device import Device

class SimEnvironment():
    def __init__(self):
        self.device_list = []
        self.message_FIFO = []

    def add_device(self, d):
        self.device_list.append(d)
        return d

    def outgoing_message(self, msg_list, channel_ID):
        # self.message_FIFO.append({"CID": channel_ID, "MSGs": msg_list})
        self.message_FIFO += msg_list

    # for now this is for a line graph
    def get_neighbors(self, source_ID):
        if source_ID is None:
            return []
        return [neigh for neigh in self.device_list if neigh.ID in [source_ID - 1, source_ID + 1]]
        
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

    test_env = SimEnvironment()

    device1 = test_env.add_device(Device(device_ID=0, sim_tx_callback=test_env.outgoing_message))
    device2 = test_env.add_device(Device(device_ID=1, sim_tx_callback=test_env.outgoing_message))
    device3 = test_env.add_device(Device(device_ID=2, sim_tx_callback=test_env.outgoing_message))

    test_env.simulate()