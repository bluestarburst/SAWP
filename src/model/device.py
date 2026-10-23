from atomic_broadcast import AtomicBroadcast
from message import Message
from random import uniform

class Device:

    #NOTE: This is kinda written s.t. all devices have the same drift characteristics, which while realistic
    #      doesn't let us do "interesting" scenarios like some small number of devices "running away" on us
    CLOCK_DRIFT_UB = 0
    CLOCK_DRIFT_LB = 0 # should be negative-valued if you want to potentially run "slow"
    CLOCK_DRIFT_FREQ = 0 # should be [0, inf) in Hz

    # sets/selects a new clock drift value
    @staticmethod
    def update_drift():
        return uniform(Device.CLOCK_DRIFT_LB, Device.CLOCK_DRIFT_UB)

    # returns the tuple (lt, ld)
    #   lt: is the new logical time after trying to wait 'duration' wall-clock time
    #   ld: is the logical duration, the wall-clock time actually waited
    def induce_clock_drift(self, logical_time, duration):
        if Device.CLOCK_DRIFT_FREQ == 0:
            return (logical_time + duration, duration)

        drift_counts = duration / Device.CLOCK_DRIFT_FREQ
        drift = drift_counts*self.clock_drift

        new_logical_time = logical_time + duration
        waited_time = duration - drift
        return (new_logical_time, waited_time)

    # What to do:
    #   I need a an initial synchronization event
    #       Each node will receive a signal at roughly the same time
    #       Based on their ID, they wait some time before broadcasting on appropriate channels
    #       This tells everyone who's alive plus elects a group leader
    #
    #   Nodes wait till a broadcast interval arrives
    #       Based on your ID, thats the order you try to broadcast in
    #       If you are second, you are right next to first, so you know if #1 AB'd if you hear from them in (f+1)*T time
    #       If you're third, you wait (f+1)*T*2
    #       If you are nth, you wait (f+1)*T*r*R, where r is your effective hop radius from ID 1, and R is your effective
    #           hop distance along that arc from the first one to you
    #
    #   The above governs how you announce yourself for the synchronization event
    #
    #   We can make it easier by doing diagonals instead of radiating out

    #NOTE: We can analyze the cycle-time of this scheme for different ID placements:
    #       Just down each row
    #       Diagonals
    #       Radiating from center

    #   Would the Device be happy to know its grid position?
    #       For routing messages to specific people, it could have a flag/TTL-esc field to mitigate flooding
    #           If you're not in the direct of the dst, you decrement the TTL and send it out
    #           If you are, you keep the TTL const.
    #       This gives us X hops to escape local minima
    #       This doesn't prevent unnecessary fanout in the direction of the destination though as +2 potentially extra people
    #           on the path receive it
    #           Maybe make the TTL decrement condition more strict: ie, you have to be on the immediate diagonal or straight to not dec?

    def __init__(self, device_ID, sim_tx_callback, assigned_channel=0):
        self.ID = device_ID
        self.AB_protocol = AtomicBroadcast(ID=device_ID, rx_callback=self.device_receive_broadcast, tx_callback=sim_tx_callback, channel_ID=assigned_channel)
        self.clock_drift = Device.update_drift()

        self.received_messages = {}
        self.current_message_ID = 0
        pass

    def work(self):
        print(f"{self.ID}: Sending")
        message = Message(self.ID, 14, self.current_message_ID, f"Hi from {self.ID}")
        self.send_message(message)

    def send_message(self, msg: Message):
        old_message_ID = self.current_message_ID
        self.current_message_ID += 1
        self.AB_protocol.broadcast(msg)
        message_tag = (self.ID, old_message_ID)
        self.received_messages[message_tag] = msg.get_encapsulated_msg()

    def sim_receive_broadcast(self, b_msg):
        self.AB_protocol.receive_broadcast(b_msg)

    def device_receive_broadcast(self, b_msg: Message):
        message_tag = (b_msg.get_original_src(), b_msg.msg_ID)
        if not message_tag in self.received_messages:
            self.received_messages[message_tag] = b_msg.get_encapsulated_msg()
            print(f"Device({self.ID}) Received: {b_msg.get_encapsulated_msg()}")
            print(f"\tTrace: {b_msg.get_msg_route()}")