from typing import Literal

CustomerAssistantActor = Literal["customer", "operator", "system"]
DEFAULT_CUSTOMER_ASSISTANT_ACTOR: CustomerAssistantActor = "customer"
