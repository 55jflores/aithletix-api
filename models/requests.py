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
                                                                            
                                                                                                                                                                                                                    
class HealthShareCardRequest(BaseModel):
    steps:          float = Field(ge=0, le=200_000)
    distance:       float = Field(ge=0, le=500)
    distance_unit:  str   = Field(max_length=10)
    calories:       float = Field(ge=0, le=20_000)
    step_streak:     int  = Field(ge=0, le=10_000)
    distance_streak: int  = Field(ge=0, le=10_000)
    calorie_streak:  int  = Field(ge=0, le=10_000)
    step_goal:      float = Field(ge=0, le=200_000)
    goal_hit:       bool  = False
    # Context fields the insight uses for interpretation rather than restating numbers.
    steps_yesterday:  float = Field(default=0, ge=0, le=200_000)
    steps_best_30d:   float = Field(default=0, ge=0, le=200_000)
    goal_hits_last_7: int   = Field(default=0, ge=0, le=7)
    dow_average:      float = Field(default=0, ge=0, le=200_000)
    day_of_week:      str   = Field(default="", max_length=12)
                                                                                                                                                                                                                    

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


class NutritionInsightRequest(BaseModel):
    workout_type:   str = Field(max_length=50)
    daily_target:   int = Field(ge=0, le=10_000)
    protein_target: int = Field(ge=0, le=500)
    protein_bonus:  int = Field(ge=0, le=100)
    goal_label:     str = Field(max_length=50)
    active_burn:    int = Field(ge=0, le=5_000)
    calories_eaten: int | None = Field(default=None, ge=0, le=15_000)
    protein_grams:  int | None = Field(default=None, ge=0, le=600)


class NutritionChatRequest(BaseModel):
    message:           str        = Field(max_length=500)
    history:           list[dict] = Field(default_factory=list, max_length=60)
    nutrition_context: str        = Field(max_length=1500)


class NutritionShareCardRequest(BaseModel):
    daily_target:   int       = Field(ge=0, le=10_000)
    protein_target: int       = Field(ge=0, le=500)
    calories_eaten: int | None = Field(default=None, ge=0, le=15_000)
    protein_grams:  int | None = Field(default=None, ge=0, le=600)
    calories_hit:   bool      = False
    protein_hit:    bool      = False


class PRSnapshot(BaseModel):
    recovery_score:      float | None = Field(default=None, ge=0, le=100)
    recovery_components: int   | None = Field(default=None, ge=1, le=3)
    bodyweight:          float | None = Field(default=None, ge=0, le=2_000)
    # Manually entered in the lift logging form — subjective recent-training
    # context, not measurement. All optional; the athlete may skip any of them.
    workouts_past_2d:    int   | None = Field(default=None, ge=0, le=50)
    last_trained:        Literal["today", "yesterday", "2_days", "3plus_days"] | None = None
    muscle_feel:         Literal["fresh", "normal", "fatigued"] | None = None


class PREntry(BaseModel):
    date:          str   = Field(max_length=10)            # "YYYY-MM-DD"
    weight_lbs:    float = Field(ge=0, le=2_000)
    reps:          int   = Field(ge=1, le=100)
    rpe:           int | None = Field(default=None, ge=1, le=10)
    estimated_1rm: float = Field(ge=0, le=3_000)
    is_bodyweight: bool  = False
    snapshot:      PRSnapshot | None = None


class PRInsightRequest(BaseModel):
    lift:    str = Field(max_length=50)
    unit:    str = Field(pattern="^(kg|lbs)$")
    entries: list[PREntry] = Field(min_length=1, max_length=60)


class CameraAlignmentInfo(BaseModel):
    quality: Literal["side_view", "off_axis"]
    ratio: float = Field(ge=0, le=10)


class RepSummary(BaseModel):
    index: int = Field(ge=1, le=100)
    top_angle: float = Field(ge=0, le=180)
    bottom_angle: float = Field(ge=0, le=180)
    range: float = Field(ge=0, le=180)
    descent_duration: float = Field(ge=0, le=60)
    ascent_duration: float = Field(ge=0, le=60)
    total_duration: float = Field(ge=0, le=120)


class DepthConsistency(BaseModel):
    mean: float = Field(ge=0, le=180)
    deepest: float = Field(ge=0, le=180)
    shallowest: float = Field(ge=0, le=180)
    range: float = Field(ge=0, le=180)
    drift: float = Field(ge=-180, le=180)
    assessment: Literal["consistent", "drifting", "insufficient_data"]


class FormMetrics(BaseModel):
    depth_consistency: DepthConsistency


class PostSetRequest(BaseModel):
    selected_lift: "Lift"                       # Lift enum already in requests.py
    rep_count: int = Field(ge=1, le=100)
    athlete_weight: float = Field(gt=0, le=1000)
    weight_unit: str = Field(pattern="^(kg|lbs)$")
    camera_alignment: Optional[CameraAlignmentInfo] = None
    reps: list[RepSummary] = Field(min_length=1, max_length=100)
    form_metrics: FormMetrics
