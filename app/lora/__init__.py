"""
LoRA Training Module

Comprehensive system for training and using LoRA models for consistent avatar generation.
"""
from app.lora.models import (
    LoraModel,
    LoraReferenceImage,
    LoraGeneratedSample,
    LoraTrainingQueue,
    LoraUsageLog,
    TrainingStatus,
    ImageValidationStatus
)
from app.lora.schemas import (
    LoraModelCreate,
    LoraModelUpdate,
    LoraModelResponse,
    LoraModelDetailResponse,
    LoraTrainingConfig,
    ReferenceImageCreate,
    ReferenceImageResponse,
    GenerateWithLoraRequest,
    GenerateWithLoraResponse,
    GeneratedSampleResponse
)
from app.lora.training_service import LoraTrainingService, get_lora_training_service
from app.lora.image_service import ImageValidationService, image_validation_service

__all__ = [
    # Models
    "LoraModel",
    "LoraReferenceImage",
    "LoraGeneratedSample",
    "LoraTrainingQueue",
    "LoraUsageLog",
    "TrainingStatus",
    "ImageValidationStatus",
    # Schemas
    "LoraModelCreate",
    "LoraModelUpdate",
    "LoraModelResponse",
    "LoraModelDetailResponse",
    "LoraTrainingConfig",
    "ReferenceImageCreate",
    "ReferenceImageResponse",
    "GenerateWithLoraRequest",
    "GenerateWithLoraResponse",
    "GeneratedSampleResponse",
    # Services
    "LoraTrainingService",
    "get_lora_training_service",
    "ImageValidationService",
    "image_validation_service"
]
