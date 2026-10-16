from atomic_broadcast import AtomicBroadcast

class Device:

    def __init__(self, device_ID, sim_tx_callback):
        self.ID = device_ID
        self.AB_protocol = AtomicBroadcast(ID=device_ID, rx_callback=self.device_receive_broadcast, tx_callback=sim_tx_callback)

        pass

    def work(self):
        print(f"{self.ID}: Sending")
        self.send_message(msg=f"Hi from {self.ID}", channel_ID=0)

    def send_message(self, msg: str, channel_ID, destination=-1):
        self.AB_protocol.broadcast(msg, channel_ID, destination)

    def sim_receive_broadcast(self, b_msg):
        self.AB_protocol.receive_broadcast(b_msg)

    def device_receive_broadcast(self, b_msg):
        print(f"Device({self.ID}) Received: {b_msg.get_encapsulated_msg()}")
        print(f"\tTrace: {b_msg.get_msg_route()}")