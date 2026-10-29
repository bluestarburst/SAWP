from atomic_broadcast import AtomicBroadcast
from message import MessageType, Message
from random import uniform
from group_membership import GroupMembership

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

    def __init__(self, device_ID, sim_tx_callback, assigned_channel=0, is_center_landmark=False, is_landmark=False):
        self.ID = device_ID
        self.AB_protocol = AtomicBroadcast(ID=device_ID, rx_callback=self.device_receive_broadcast, tx_callback=sim_tx_callback, channel_ID=assigned_channel)
        self.Group_Membership = GroupMembership(device_id=device_ID, device_broadcast_cb=self.AB_protocol.broadcast, device_msg_ID_cb=self.inc_message_ID_callback, is_chief_landmark=is_center_landmark, is_landmark=is_landmark)
        self.clock_drift = Device.update_drift()

        self.received_messages = {}
        self.current_message_ID = 0
        # Each device keeps its own view and a new group request clears it
        self.group_id = None
        self.group_members = set()
        self.survey_routes = {}
        self.group_announced = False

        self.is_chief_landmark = is_center_landmark
        self.is_landmark = is_landmark

    def inc_message_ID_callback(self):
        self.current_message_ID += 1
        return self.current_message_ID

    # def work(self):
    #     print(f"{self.ID}: Sending")
    #     message = Message(self.ID, 14, self.current_message_ID, f"Hi from {self.ID}")
    #     self.send_message(message)

    def send_message(self, msg: Message):
        old_message_ID = self.current_message_ID
        self.current_message_ID += 1
        # Every control message needs a fresh ID even within the same phase
        msg.msg_ID = old_message_ID
        self.AB_protocol.broadcast(msg)
        message_tag = (self.ID, old_message_ID)
        self.received_messages[message_tag] = msg.get_encapsulated_msg()


    def sim_receive_broadcast(self, b_msg: Message):

        #Group Membership snooping
        match b_msg.kind:
            case MessageType.GROUP_REQUEST:
                self.Group_Membership.saw_new_group_message()
            case MessageType.LANDMARK_SURVEY:
                route = b_msg.get_msg_route() #get rid of -1 if its in ???
                while -1 in route:
                    route.remove(-1)
                self.Group_Membership.note_route_surveyed(route)
                pass
            case MessageType.LANDMARK_SURVEY_RESULTS:
                if self.is_chief_landmark:
                    members: list = b_msg.get_encapsulated_msg()
                    self.Group_Membership.seen_survey_results(members)
                pass
            case MessageType.GROUP_ANNOUNCE:
                members: list = b_msg.get_encapsulated_msg()
                self.Group_Membership.seen_group_announce(members)
                pass
            case MessageType.GROUP_JOIN:
                stragler_ID = b_msg.get_original_src()
                self.Group_Membership.add_group_stragler(stragler_ID)
                pass
            case _:
                pass

        self.AB_protocol.receive_broadcast(b_msg)

    
    def sim_step_changed(self, new_sim_step):
        self.Group_Membership.simulation_advanced(new_sim_step)
        # + any other "async" events/structures that would need it


    def device_receive_broadcast(self, b_msg: Message):
        message_tag = (b_msg.get_original_src(), b_msg.msg_ID)
        if not message_tag in self.received_messages:
            self.received_messages[message_tag] = b_msg.get_encapsulated_msg()
            print(f"Device({self.ID}) Received: {b_msg.get_encapsulated_msg()}")
            print(f"\tTrace: {b_msg.get_msg_route()}")

    def __str__(self) -> str:
        return f"{self.ID}"# {str(self.Group_Membership)}"

