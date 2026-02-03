"""Tracks agent interactions and calculates performance metrics."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json


class InteractionType(str, Enum):
    """Types of interactions to track."""
    PAGE_LOAD = "page_load"
    FIELD_FILL = "field_fill"
    FIELD_FILL_ATTEMPT = "field_fill_attempt"
    BUTTON_CLICK = "button_click"
    BUTTON_CLICK_ATTEMPT = "button_click_attempt"
    DROPDOWN_SELECT = "dropdown_select"
    CHECKBOX_TOGGLE = "checkbox_toggle"
    RADIO_SELECT = "radio_select"
    FILE_UPLOAD = "file_upload"
    NAVIGATION = "navigation"
    VALIDATION_ERROR = "validation_error"
    PAGE_TIMEOUT = "page_timeout"
    ELEMENT_NOT_FOUND = "element_not_found"


@dataclass
class Interaction:
    """Single interaction event."""
    timestamp: datetime
    interaction_type: InteractionType
    element_id: Optional[str] = None
    element_selector: Optional[str] = None
    element_label: Optional[str] = None
    action: Optional[str] = None  # e.g., "click", "fill", "select"
    value: Optional[Any] = None  # Value that was set/selected
    success: bool = True
    error_message: Optional[str] = None
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    duration_ms: Optional[float] = None  # Time taken for this interaction
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldInteraction:
    """Detailed tracking for a specific field."""
    field_id: str
    field_name: str
    field_label: str
    field_type: str
    required: bool
    attempts: List[Interaction] = field(default_factory=list)
    final_value: Optional[Any] = None
    was_filled: bool = False
    was_filled_correctly: bool = False
    validation_errors: List[str] = field(default_factory=list)
    time_to_fill_ms: Optional[float] = None


@dataclass
class PageMetrics:
    """Metrics for a single page/stage."""
    page_id: str
    page_url: str
    page_title: str
    load_time_ms: Optional[float] = None
    time_on_page_ms: Optional[float] = None
    fields_total: int = 0
    fields_required: int = 0
    fields_filled: int = 0
    fields_filled_correctly: int = 0
    buttons_clicked: int = 0
    buttons_click_attempts: int = 0
    validation_errors: int = 0
    interactions: List[Interaction] = field(default_factory=list)
    field_interactions: Dict[str, FieldInteraction] = field(default_factory=dict)


@dataclass
class TestSessionMetrics:
    """Complete metrics for a test session."""
    session_id: str
    template_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_visited: List[str] = field(default_factory=list)
    pages_completed: List[str] = field(default_factory=list)
    total_pages: int = 0
    pages_metrics: Dict[str, PageMetrics] = field(default_factory=dict)
    total_interactions: int = 0
    successful_interactions: int = 0
    failed_interactions: int = 0
    total_fields: int = 0
    fields_filled: int = 0
    fields_filled_correctly: int = 0
    fields_missed: List[str] = field(default_factory=list)
    fields_incorrect: List[str] = field(default_factory=list)
    buttons_clicked: int = 0
    buttons_failed: int = 0
    navigation_errors: int = 0
    validation_errors: int = 0
    total_duration_ms: Optional[float] = None
    success: bool = False
    completion_percentage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class InteractionTracker:
    """Tracks all interactions during agent testing."""
    
    def __init__(self, session_id: str, template_id: str):
        """Initialize tracker for a test session."""
        self.session_id = session_id
        self.template_id = template_id
        self.start_time = datetime.now()
        self.interactions: List[Interaction] = []
        self.current_page_id: Optional[str] = None
        self.current_page_url: Optional[str] = None
        self.metrics = TestSessionMetrics(
            session_id=session_id,
            template_id=template_id,
            start_time=self.start_time
        )
    
    def track_interaction(
        self,
        interaction_type: InteractionType,
        element_id: Optional[str] = None,
        element_selector: Optional[str] = None,
        element_label: Optional[str] = None,
        action: Optional[str] = None,
        value: Optional[Any] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        page_url: Optional[str] = None,
        page_title: Optional[str] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track a single interaction."""
        interaction = Interaction(
            timestamp=datetime.now(),
            interaction_type=interaction_type,
            element_id=element_id,
            element_selector=element_selector,
            element_label=element_label,
            action=action,
            value=value,
            success=success,
            error_message=error_message,
            page_url=page_url or self.current_page_url,
            page_title=page_title,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        self.interactions.append(interaction)
        self.metrics.total_interactions += 1
        
        if success:
            self.metrics.successful_interactions += 1
        else:
            self.metrics.failed_interactions += 1
        
        # Update page metrics
        if self.current_page_id:
            if self.current_page_id not in self.metrics.pages_metrics:
                self.metrics.pages_metrics[self.current_page_id] = PageMetrics(
                    page_id=self.current_page_id,
                    page_url=self.current_page_url or "",
                    page_title=""
                )
            
            page_metrics = self.metrics.pages_metrics[self.current_page_id]
            page_metrics.interactions.append(interaction)
            
            # Update specific counters
            if interaction_type == InteractionType.FIELD_FILL and success:
                page_metrics.fields_filled += 1
            elif interaction_type == InteractionType.BUTTON_CLICK and success:
                page_metrics.buttons_clicked += 1
            elif interaction_type == InteractionType.BUTTON_CLICK_ATTEMPT:
                page_metrics.buttons_click_attempts += 1
            elif interaction_type == InteractionType.VALIDATION_ERROR:
                page_metrics.validation_errors += 1
    
    def set_current_page(self, page_id: str, page_url: str, page_title: str = ""):
        """Set the current page being tracked."""
        self.current_page_id = page_id
        self.current_page_url = page_url
        
        if page_id not in self.metrics.pages_metrics:
            self.metrics.pages_metrics[page_id] = PageMetrics(
                page_id=page_id,
                page_url=page_url,
                page_title=page_title
            )
        
        if page_id not in self.metrics.pages_visited:
            self.metrics.pages_visited.append(page_id)
        
        self.track_interaction(
            interaction_type=InteractionType.PAGE_LOAD,
            page_url=page_url,
            page_title=page_title
        )
    
    def track_field_fill(
        self,
        field_id: str,
        field_name: str,
        field_label: str,
        field_type: str,
        value: Any,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Track a field fill attempt."""
        self.track_interaction(
            interaction_type=InteractionType.FIELD_FILL if success else InteractionType.FIELD_FILL_ATTEMPT,
            element_id=field_id,
            element_selector=f"#{field_id}",
            element_label=field_label,
            action="fill",
            value=value,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            metadata={"field_name": field_name, "field_type": field_type}
        )
        
        # Update field-specific tracking
        if self.current_page_id:
            page_metrics = self.metrics.pages_metrics.get(self.current_page_id)
            if page_metrics:
                if field_id not in page_metrics.field_interactions:
                    page_metrics.field_interactions[field_id] = FieldInteraction(
                        field_id=field_id,
                        field_name=field_name,
                        field_label=field_label,
                        field_type=field_type,
                        required=False  # Will be updated from template
                    )
                
                field_tracking = page_metrics.field_interactions[field_id]
                field_tracking.attempts.append(self.interactions[-1])
                if success:
                    field_tracking.was_filled = True
                    field_tracking.final_value = value
                else:
                    if error_message:
                        field_tracking.validation_errors.append(error_message)
    
    def track_button_click(
        self,
        button_id: Optional[str],
        button_selector: str,
        button_text: str,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Track a button click attempt."""
        interaction_type = InteractionType.BUTTON_CLICK if success else InteractionType.BUTTON_CLICK_ATTEMPT
        
        self.track_interaction(
            interaction_type=interaction_type,
            element_id=button_id,
            element_selector=button_selector,
            element_label=button_text,
            action="click",
            success=success,
            error_message=error_message,
            duration_ms=duration_ms
        )
        
        if success:
            self.metrics.buttons_clicked += 1
        else:
            self.metrics.buttons_failed += 1
    
    def finalize_session(self, success: bool = False):
        """Finalize the test session and calculate final metrics."""
        self.metrics.end_time = datetime.now()
        self.metrics.total_duration_ms = (
            (self.metrics.end_time - self.metrics.start_time).total_seconds() * 1000
        )
        self.metrics.success = success
        
        # Calculate completion percentage
        total_required_fields = sum(
            len([f for f in page.fields if f.required])
            for page in []  # Will be populated from template
        )
        
        if total_required_fields > 0:
            self.metrics.completion_percentage = (
                self.metrics.fields_filled_correctly / total_required_fields
            ) * 100
    
    def get_metrics(self) -> TestSessionMetrics:
        """Get current metrics."""
        return self.metrics
    
    def export_to_json(self, filepath: str):
        """Export all tracking data to JSON file."""
        data = {
            "session_id": self.session_id,
            "template_id": self.template_id,
            "start_time": self.metrics.start_time.isoformat(),
            "end_time": self.metrics.end_time.isoformat() if self.metrics.end_time else None,
            "total_duration_ms": self.metrics.total_duration_ms,
            "success": self.metrics.success,
            "completion_percentage": self.metrics.completion_percentage,
            "interactions": [
                {
                    "timestamp": i.timestamp.isoformat(),
                    "type": i.interaction_type.value,
                    "element_id": i.element_id,
                    "element_selector": i.element_selector,
                    "element_label": i.element_label,
                    "action": i.action,
                    "value": str(i.value) if i.value is not None else None,
                    "success": i.success,
                    "error_message": i.error_message,
                    "page_url": i.page_url,
                    "duration_ms": i.duration_ms,
                    "metadata": i.metadata
                }
                for i in self.interactions
            ],
            "metrics": {
                "total_interactions": self.metrics.total_interactions,
                "successful_interactions": self.metrics.successful_interactions,
                "failed_interactions": self.metrics.failed_interactions,
                "fields_filled": self.metrics.fields_filled,
                "fields_filled_correctly": self.metrics.fields_filled_correctly,
                "fields_missed": self.metrics.fields_missed,
                "fields_incorrect": self.metrics.fields_incorrect,
                "buttons_clicked": self.metrics.buttons_clicked,
                "buttons_failed": self.metrics.buttons_failed,
                "validation_errors": self.metrics.validation_errors
            },
            "pages": {
                page_id: {
                    "page_id": pm.page_id,
                    "page_url": pm.page_url,
                    "fields_total": pm.fields_total,
                    "fields_filled": pm.fields_filled,
                    "fields_filled_correctly": pm.fields_filled_correctly,
                    "buttons_clicked": pm.buttons_clicked,
                    "validation_errors": pm.validation_errors,
                    "time_on_page_ms": pm.time_on_page_ms
                }
                for page_id, pm in self.metrics.pages_metrics.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
