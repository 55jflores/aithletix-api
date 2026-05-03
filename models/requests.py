from pydantic import BaseModel, Field, field_validator                                                                                                                                                             
from typing import Optional, Annotated, Literal
from enum import Enum                                                                                                                                                                                              
                                                                            
                                                                                                                                                                                                                    
class Lift(str, Enum):
    squat = "Squat"                                                                                                                                                                                                
    deadlift = "Deadlift"
    bench = "Bench Press"                                                                                                                                                                                          
                                                                            
                                                                            
_REQUIRED_PAYLOAD_SECTIONS = [                                                
    "=== AthleteIQ Physics Context ===",                                                                                                                                                                           
    "--- Session ---",
    "--- Joint Angles ---",                                                                                                                                                                                        
    "--- Torque Analysis ---",                                               
    "--- Stability ---",                                                                                                                                                                                           
]                                     
                                                                                                                                                                                                                    
def _validate_payload(v: str) -> str:                                         
    for section in _REQUIRED_PAYLOAD_SECTIONS:                                                                                                                                                                     
        if section not in v:
            raise ValueError(f"Payload missing required section: {section}")                                                                                                                                       
    return v                                                                  
                                                                                                                                                                                                                    
                
class RealtimeCoachingRequest(BaseModel):                                                                                                                                                                          
    payload: str = Field(max_length=2500)
    selected_lift: Lift                                                                                                                                                                                            
    athlete_weight: float = Field(gt=0, le=1000)                              
    weight_unit: str = Field(pattern="^(kg|lbs)$")
                                                                            
    @field_validator("payload")                                                                                                                                                                                    
    @classmethod                      
    def validate_payload_structure(cls, v):                                                                                                                                                                        
        return _validate_payload(v)                                                                                                                                                                                
                                                                            
                                                                                                                                                                                                                    
class PostSetRequest(BaseModel):
    payload_history: list[Annotated[str, Field(max_length=2500)]] = Field(max_length=30)                                                                                                                           
    selected_lift: Lift                                                      
    rep_count: int = Field(ge=1, le=100)                                                                                                                                                                           
    athlete_weight: float = Field(gt=0, le=1000)
    weight_unit: str = Field(pattern="^(kg|lbs)$")                           
                                                                                                                                                                                                                    
    @field_validator("payload_history")
    @classmethod                                                                                                                                                                                                   
    def validate_snapshot_structures(cls, v):                                                                                                                                                                      
        for snapshot in v:
            _validate_payload(snapshot)                                                                                                                                                                            
        return v                                                              
                                    
class Message(BaseModel):                                                                                                                                                                                          
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)                                                                                                                                                                          
                                                                            
                                                                            
class ChatRequest(BaseModel):         
    message: str = Field(max_length=1000)
    conversation_history: list[Message] = Field(max_length=50)                                                                                                                                                     
    current_payload: Optional[str] = Field(default=None, max_length=2500)    
    athlete_weight: float = Field(gt=0, le=1000)                                                                                                                                                                   
    weight_unit: str = Field(pattern="^(kg|lbs)$")                           
                                                                            
    @field_validator("current_payload")                                                                                                                                                                            
    @classmethod
    def validate_current_payload_structure(cls, v):                                                                                                                                                                
        if v is not None:                                                    
            _validate_payload(v)                                                                                                                                                                                   
        return v                      
                                                                                                                                                                                                                    
class HealthChatRequest(BaseModel):                                           
    message:        str       = Field(max_length=500)                                                                                                                                                              
    history:        list[dict] = Field(default_factory=list, max_length=60)
    health_context: str       = Field(max_length=1500)                                                                                                                                                             
                                                                            
                                                                                                                                                                                                                    
class ShareCardSummaryRequest(BaseModel):
    steps:           float
    distance:        float                                                                                                                                                                                         
    distance_unit:   str
    calories:        float                                                                                                                                                                                         
    step_streak:     int
    distance_streak: int                                                     
    calorie_streak:  int                                                      
    step_goal:       float            
    goal_hit:        bool
                                                                                                                                                                                                                    

class SnapshotRequest(BaseModel):                                                                                                                                                                                  
    steps_today:            float = Field(ge=0)
    steps_recent_avg:       float = Field(ge=0)                              
    steps_long_term_avg:    float = Field(ge=0)                               
    steps_best_day:         float = Field(ge=0)
    steps_goal:             float = Field(ge=0)
    step_streak:            int   = Field(ge=0)                                                                                                                                                                    
    steps_yesterday:        float = Field(ge=0)                               
    steps_this_week:        float = Field(ge=0)                                                                                                                                                                    
    steps_last_week:        float = Field(ge=0)
    steps_goal_days:        int   = Field(ge=0, le=7)                                                                                                                                                              
    distance_today:         float = Field(ge=0)                               
    distance_recent_avg:    float = Field(ge=0)                                                                                                                                                                    
    distance_long_term_avg: float = Field(ge=0)                              
    distance_best_day:      float = Field(ge=0)                                                                                                                                                                    
    distance_unit:          str   = Field(pattern="^(mi|km)$")
    distance_streak:        int   = Field(ge=0)                                                                                                                                                                    
    distance_this_week:     float = Field(ge=0)                                                                                                                                                                    
    distance_last_week:     float = Field(ge=0)
    calories_today:         float = Field(ge=0)                                                                                                                                                                    
    calories_recent_avg:    float = Field(ge=0)                                                                                                                                                                    
    calories_long_term_avg: float = Field(ge=0)                               
    calories_best_day:      float = Field(ge=0)                                                                                                                                                                    
    calorie_streak:         int   = Field(ge=0)                              
    calories_this_week:     float = Field(ge=0)                                                                                                                                                                    
    calories_last_week:     float = Field(ge=0)
    time_of_day:            str   = Field(pattern="^(morning|afternoon|evening)$") 
    force_refresh:          bool  = False
    date: str = Field(pattern=r"^\w+, \w+ \d{2}, \d{4}$")  # e.g. "Friday, May 02, 2025"

