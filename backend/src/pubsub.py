import logging

EVENT_NEW_POST = "new_post"
EVENT_FILTERED_POST = "filtered_post"
EVENT_FULL_POST = "full_post"

logger = logging.getLogger(__name__)


class PubSub:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, callback):
        logger.info(f"Add subscriber for {event_type}")
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback):
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                cb for cb in self.subscribers[event_type] if cb != callback
            ]

    def publish(self, event_type: str, data):
        logger.info(f"Attempt to find callback for {event_type}")
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                logger.info(f"Find callback for {event_type}")
                callback(data)

    def get_subscriber_count(self, event_type: str) -> int:
        return len(self.subscribers.get(event_type, []))
