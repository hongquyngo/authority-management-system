from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class AuthorityType:
    """Base authority type"""
    id: int
    code: str
    name: str
    description: str
    is_active: bool = True

@dataclass
class Authority:
    """Base authority assignment"""
    id: int
    employee_id: int
    type_id: int
    entity_id: Optional[int]
    is_active: bool
    valid_from: datetime
    valid_to: Optional[datetime]
    created_by: str
    created_date: datetime
    
class BaseAuthorityService(ABC):
    """Abstract base class for authority services"""
    
    @abstractmethod
    def get_types(self) -> List[AuthorityType]:
        """Get all authority types"""
        pass
    
    @abstractmethod
    def get_authorities(self, filters: Dict) -> List[Authority]:
        """Get authorities with filters"""
        pass
    
    @abstractmethod
    def add_authority(self, data: Dict) -> bool:
        """Add new authority"""
        pass
    
    @abstractmethod
    def update_authority(self, id: int, data: Dict) -> bool:
        """Update authority"""
        pass
    
    @abstractmethod
    def delete_authority(self, id: int) -> bool:
        """Delete authority"""
        pass
    
    @abstractmethod
    def validate_authority(self, data: Dict) -> List[str]:
        """Validate authority data"""
        pass

class BaseAuthorityView(ABC):
    """Abstract base class for authority views"""
    
    @abstractmethod
    def render(self):
        """Main render method"""
        pass
    
    @abstractmethod
    def render_list_view(self):
        """Render list/search view"""
        pass
    
    @abstractmethod
    def render_form_view(self):
        """Render add/edit form"""
        pass
    
    @abstractmethod
    def render_import_view(self):
        """Render import view"""
        pass