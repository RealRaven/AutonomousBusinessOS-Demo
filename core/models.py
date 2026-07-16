# core/models.py
from dataclasses import dataclass, asdict

@dataclass
class Customer:
    customer_id: str = ""
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    customer_company: str = ""
    customer_address: str = ""
    customer_notes: str = ""
    
    def to_text(self) -> str:
        """Convert customer to searchable text for embedding"""
        parts = [
            f"Name: {self.customer_name}",
            f"Email: {self.customer_email}",
            f"Phone: {self.customer_phone}",
            f"Company: {self.customer_company}",
            f"Address: {self.customer_address}",
            f"Notes: {self.customer_notes}",
        ]
        return " | ".join(filter(lambda x: ": " in x and not x.endswith(": "), parts))
    
    def to_dict(self) -> dict:
        return asdict(self)