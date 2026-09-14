"""Director project planning and resume services."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeVar
import logging

from pydantic import BaseModel

from app.director.brief import CreativeBrief
from app.director.director import build_brief, build_script, build_storyboard
from app.director.schemas import Script, Storyboard, validate_storyboard_duration
from app.models.project import ProjectStatus, VideoProject
from app.models.run import GenerationRun
from app.models.timeline import Timeline, TimelineScene
from app.providers.base import LLMProvider
from app.storage.filesystem import FilesystemStore
from app.storage.runs import GenerationRunStore

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
